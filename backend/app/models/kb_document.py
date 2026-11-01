from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class KbDocument(Base):
    __tablename__ = "kb_documents"
    __table_args__ = {"comment": "知识库文档"}

    original_name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, comment="原始文件名"
    )
    disk_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="磁盘文件名"
    )
    rel_path: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="相对于 data/kb 的保存路径"
    )
    size: Mapped[int] = mapped_column(Integer, nullable=False, comment="实际保存的字节数")
    ext: Mapped[str] = mapped_column(String(20), nullable=False, comment="小写扩展名")
    ingested: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否已写入共享向量库"
    )
