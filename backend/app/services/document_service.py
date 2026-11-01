import logging
import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.config import KB_ALLOWED_EXTENSIONS, KB_DIR, MAX_FILE_SIZE
from app.models.kb_document import KbDocument
from app.schemas.document import DocumentPreviewResponse, KbDocumentResponse
from app.services.rag_service import (
    delete_by_doc_id,
    extract_document_text,
    ingest_kb_file,
)

logger = logging.getLogger(__name__)

_READ_BLOCK_SIZE = 64 * 1024


def _cleanup_vectors(doc_ids: list[int]) -> None:
    """尽力清理本批已写入的向量片段，失败只记录日志。"""
    for doc_id in doc_ids:
        try:
            delete_by_doc_id(doc_id)
        except Exception:
            logger.exception("清理向量片段失败：doc_id=%s", doc_id)


def _cleanup_files(paths: list[Path]) -> None:
    """尽力清理本批已写入的原文件，失败只记录日志。"""
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.exception("清理原文件失败：%s", path)


def list_documents(db: Session) -> list[KbDocumentResponse]:
    """按 id 倒序返回全部资料记录。"""
    rows = db.scalars(select(KbDocument).order_by(KbDocument.id.desc())).all()
    return [KbDocumentResponse.model_validate(row) for row in rows]


def get_document(db: Session, doc_id: int) -> KbDocument:
    """查询单份资料；不存在时返回 404 业务错误。"""
    row = db.scalar(select(KbDocument).where(KbDocument.id == doc_id))
    if row is None:
        raise BusinessException(message="文档不存在", code=404)
    return row


def _get_document_for_update(db: Session, doc_id: int) -> KbDocument:
    """锁定一份资料，避免删除和重新入库同时改写它的向量。"""
    row = db.scalar(
        select(KbDocument).where(KbDocument.id == doc_id).with_for_update()
    )
    # 只有存在的资料才能进入后续向量操作，避免按无效 ID 清理。
    if row is None:
        raise BusinessException(message="文档不存在", code=404)
    return row


def document_path(rel_path: str) -> Path:
    """把相对路径还原为 data/kb 下的完整文件路径。"""
    return KB_DIR / rel_path


def upload_documents(
    db: Session, files: list[UploadFile]
) -> list[KbDocumentResponse]:
    """本批所有文件和向量都成功后才提交资料记录。"""
    if not files:
        raise BusinessException(message="请至少上传一个文件", code=400)

    saved_paths: list[Path] = []  # 本批创建的原文件，失败时逐个删除
    rows: list[KbDocument] = []  # 本批新增的记录，flush 后取得 ID 供向量标记
    names: set[str] = set()  # 本批已使用的原始文件名，防止批内重名

    try:
        for file in files:
            original_name = os.path.basename(file.filename or "")
            if not original_name:
                raise BusinessException(message="文件名不能为空", code=400)

            ext = Path(original_name).suffix.lower()
            if ext not in KB_ALLOWED_EXTENSIONS:
                raise BusinessException(
                    message=f"不支持的文件类型：{ext}", code=400
                )
            if original_name in names:
                raise BusinessException(
                    message=f"同一批中存在重复文件：{original_name}", code=400
                )
            exists = db.scalar(
                select(KbDocument).where(KbDocument.original_name == original_name)
            )
            if exists is not None:
                raise BusinessException(
                    message=f"已存在同名文档：{original_name}", code=400
                )
            names.add(original_name)

            # 磁盘名与原名解耦，避免直接使用上传者提供的路径。
            disk_name = f"{uuid.uuid4().hex}{ext}"
            save_path = KB_DIR / disk_name
            size = 0
            with open(save_path, "xb") as target:
                while True:
                    block = file.file.read(_READ_BLOCK_SIZE)
                    if not block:
                        break
                    size += len(block)
                    if size > MAX_FILE_SIZE:
                        raise BusinessException(
                            message=f"文件不能超过 {MAX_FILE_SIZE // 1024 // 1024}MB",
                            code=400,
                        )
                    target.write(block)
            saved_paths.append(save_path)

            if size == 0:
                raise BusinessException(
                    message=f"文件内容为空：{original_name}", code=400
                )

            row = KbDocument(
                original_name=original_name,
                disk_name=disk_name,
                rel_path=disk_name,
                size=size,
                ext=ext,
                ingested=False,
            )
            db.add(row)
            rows.append(row)

        # 先取得文档 ID，才能为每块写入 doc_id。
        db.flush()
        for row in rows:
            ingest_kb_file(row.id, row.original_name, document_path(row.rel_path))
            row.ingested = True

        # 全部入库完成后只提交一次，保证本批记录与向量状态一致。
        db.commit()
        return [KbDocumentResponse.model_validate(row) for row in rows]

    except BusinessException:
        row_ids = [row.id for row in rows if row.id is not None]
        db.rollback()
        _cleanup_vectors(row_ids)
        _cleanup_files(saved_paths)
        raise
    except Exception as exc:
        row_ids = [row.id for row in rows if row.id is not None]
        db.rollback()
        _cleanup_vectors(row_ids)
        _cleanup_files(saved_paths)
        logger.exception("批量上传资料失败")
        raise BusinessException(
            message="资料上传失败，请检查向量服务与后端日志"
        ) from exc


def delete_document(db: Session, doc_id: int) -> None:
    """先清理向量，确认记录已删除后再清理原文件。"""
    row = _get_document_for_update(db, doc_id)
    try:
        # 不论状态是否已入库，都按文档 ID 清理，处理此前失败留下的残留片段。
        delete_by_doc_id(row.id)
    except Exception as exc:
        logger.exception("清理文档向量失败：doc_id=%s", doc_id)
        raise BusinessException(message="向量清理失败，请稍后重试") from exc

    db.delete(row)
    db.commit()

    path = document_path(row.rel_path)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("删除原文件失败：%s", path)
        raise BusinessException(
            message="资料记录和向量已删除，但原文件清理失败"
        )


def reingest_document(db: Session, doc_id: int) -> KbDocumentResponse:
    """清理旧片段后重新入库；失败时保留原文件和记录。"""
    row = _get_document_for_update(db, doc_id)
    path = document_path(row.rel_path)
    try:
        if not path.exists():
            raise BusinessException(message="原文件不存在，无法重新入库")
        ingest_kb_file(row.id, row.original_name, path)
        row.ingested = True
        db.commit()
        db.refresh(row)
        return KbDocumentResponse.model_validate(row)
    except BusinessException:
        db.rollback()
        row = _get_document_for_update(db, doc_id)
        # 入库失败后状态修正为“未入库”，修好配置后可再次重试。
        row.ingested = False
        db.commit()
        raise
    except Exception as exc:
        db.rollback()
        row = _get_document_for_update(db, doc_id)
        row.ingested = False
        db.commit()
        logger.exception("重新入库失败：doc_id=%s", doc_id)
        raise BusinessException(
            message="重新入库失败，请检查向量服务与后端日志"
        ) from exc


def preview_document(db: Session, doc_id: int) -> DocumentPreviewResponse:
    """提取资料纯文本用于预览，不还原原始版式。"""
    row = get_document(db, doc_id)
    text = extract_document_text(document_path(row.rel_path))
    return DocumentPreviewResponse(
        id=row.id,
        original_name=row.original_name,
        ext=row.ext,
        text=text,
        char_count=len(text),
    )
