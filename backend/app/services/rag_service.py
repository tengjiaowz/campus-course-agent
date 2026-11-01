import logging
from pathlib import Path

from docx import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.common.exceptions import BusinessException
from app.config import settings

logger = logging.getLogger(__name__)

# 分块长度与重叠量；向量接口单次最多提交 32 个片段。
_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 50
_EMBED_BATCH_SIZE = 32


def extract_document_text(path: Path) -> str:
    """按扩展名提取资料纯文本；不支持或无法解析时给出明确错误。"""
    ext = path.suffix.lower()
    try:
        if ext in {".txt", ".md"}:
            text = path.read_text(encoding="utf-8")
        elif ext == ".pdf":
            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == ".docx":
            document = Document(str(path))
            parts = [paragraph.text for paragraph in document.paragraphs]
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        parts.append(cell.text)
            text = "\n".join(parts)
        else:
            raise BusinessException(message=f"不支持的文件类型：{ext}")
    except BusinessException:
        raise
    except Exception as exc:
        logger.exception("提取文档文字失败：%s", path)
        raise BusinessException(message="无法读取文档内容，请确认文件未损坏") from exc

    text = text.strip()
    # 空文档没有可入库的内容，明确报错而不是写入空片段。
    if not text:
        raise BusinessException(message="文档中没有可提取的文字")
    return text


def _embeddings() -> OpenAIEmbeddings:
    """创建向量模型客户端；缺少密钥时在调用前给出明确错误。"""
    # 未配置密钥时先停止，避免将配置缺失误判为远程服务故障。
    if not settings.EMBEDDING_API_KEY:
        raise BusinessException(message="请先配置 EMBEDDING_API_KEY", code=500)
    return OpenAIEmbeddings(
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL,
        model=settings.EMBEDDING_MODEL,
        # 兼容本节所用的 OpenAI 兼容服务，避免先按 OpenAI token 规则拆输入。
        check_embedding_ctx_length=False,
        # 一次最多提交 32 个片段，较长资料也分批调用 Embedding 接口。
        chunk_size=_EMBED_BATCH_SIZE,
    )


def get_vectorstore() -> Chroma:
    """连接共享 Chroma 服务；FastAPI 与 MCP 都通过该服务读写。"""
    return Chroma(
        collection_name=settings.CHROMA_COLLECTION,
        embedding_function=_embeddings(),
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
    )


def ingest_kb_file(doc_id: int, source: str, path: Path) -> None:
    """提取、分块并写入向量库；同一文档重复入库先清理旧片段。"""
    text = extract_document_text(path)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE,
        chunk_overlap=_CHUNK_OVERLAP,
    )
    chunks = splitter.split_text(text)
    if not chunks:
        raise BusinessException(message="文档中没有可入库的片段")

    store = get_vectorstore()
    # 先移除该文档的旧片段，重新入库不会累积重复片段。
    store.delete(where={"doc_id": str(doc_id)})
    ids = [f"doc-{doc_id}-chunk-{index}" for index in range(len(chunks))]
    metadatas = [
        {"doc_id": str(doc_id), "source": source, "scope": "kb"} for _ in chunks
    ]
    # 向量接口单次最多 32 条，按批写入 Chroma。
    for start in range(0, len(chunks), _EMBED_BATCH_SIZE):
        end = start + _EMBED_BATCH_SIZE
        store.add_texts(
            texts=chunks[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end],
        )


def delete_by_doc_id(doc_id: int) -> None:
    """按文档 ID 清理向量片段，不删除整个集合。"""
    get_vectorstore().delete(where={"doc_id": str(doc_id)})


def search_docs(query: str) -> dict:
    """检索最相近的 3 个片段，区分服务失败与没有可用片段。"""
    question = query.strip()
    # 空白问题没有可检索的含义，直接返回输入错误，不调用向量模型。
    if not question:
        return {"ok": False, "error": "检索问题不能为空", "items": []}
    try:
        # 问题向量与资料向量使用同一模型，最多取三个相近片段供模型判断依据。
        documents = get_vectorstore().similarity_search(question, k=3)
    except BusinessException as exc:
        return {"ok": False, "error": exc.message, "items": []}
    except Exception:
        logger.exception("检索课程资料失败")
        return {"ok": False, "error": "资料检索服务暂不可用", "items": []}

    items = [
        {"content": document.page_content, "source": document.metadata.get("source", "")}
        for document in documents
    ]
    # ok=True 且 items 为空表示检索成功但没有可用片段，区别于服务失败。
    return {"ok": True, "error": "", "items": items}
