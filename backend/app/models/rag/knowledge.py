"""知识库（KnowledgeBase）的数据库模型定义。
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.services.database import Base


class KnowledgeBase(Base):
    """一条记录表示一个知识库（名称全局唯一，可挂多篇文档）。"""
    __tablename__ = "knowledge_bases"
    # 主键：Integer=整型列；primary_key=主键（非空、唯一标识一行，SQLite 下常配合自增）；index=True=建索引加快按 id 查询
    id = Column(Integer, primary_key=True, index=True)

    # 知识库名称：String=短文本；nullable=False=插入/更新时不能为 NULL
    name = Column(String, nullable=False, unique=True)

    # 描述：Text=长文本类型（无长度上限约定）
    description = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # 关联文档（一对多）
    # back_populates 与 Document 类里同名关系字段对应，双向导航
    # cascade="all, delete"：删除知识库时自动删除下面所有文档（仅 ORM/数据库层行为，不删磁盘文件）
    documents = relationship(
        "Document",
        back_populates="knowledge_base",
        cascade="all, delete"
    )

