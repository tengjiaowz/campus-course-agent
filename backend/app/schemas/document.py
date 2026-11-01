from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KbDocumentResponse(BaseModel):
    """上传结果和资料列表共用的资料记录。"""

    id: int
    original_name: str  # 上传时的文件名，供页面显示
    disk_name: str  # 为避免重名而生成的磁盘文件名
    rel_path: str  # 相对于 data/kb 的保存路径
    size: int
    ext: str
    create_time: datetime
    ingested: bool  # 页面展示的入库状态；false 的旧资料可以重新入库

    model_config = ConfigDict(from_attributes=True)


class DocumentPreviewResponse(BaseModel):
    """资料纯文本预览结果。"""

    id: int
    original_name: str
    ext: str
    text: str
    char_count: int
