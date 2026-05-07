# 链接 sqlite 数据库
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# sqlite 数据库地址
DATABASE_URL = "sqlite:///data/db.sqlite3"

# 创建数据库引擎
engine = create_engine(
  DATABASE_URL,
  connect_args={"check_same_thread": False}
)

# 创建数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建 ORM 基类
Base = declarative_base()