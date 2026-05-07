from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship
from datetime import datetime
from app.services.database import Base


class Document(Base):
    __tablename__ = "documents"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 文档名称-非空
    name = Column(String, nullable=False)

    # 文件路径
    file_path = Column(String, nullable=False)

    # 文档内容
    content = Column(Text)

    # 文档状态
    status = Column(
        String,
        default="pending"
    )

    # 所属知识库ID
    knowledge_base_id = Column(
        Integer,
        ForeignKey("knowledge_bases.id")
    )

    # 创建时间
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # 关联知识库
    knowledge_base = relationship(
        "KnowledgeBase",
        back_populates="documents"
    )