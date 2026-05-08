import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.database import Base, engine
from loguru import logger
from app.api.routes import router
from app.core.rag.rag_flow.rag_flow import build_index, check_index
import app.models.rag.knowledge       # noqa: F401
import app.models.rag.knowledge_docs  # noqa: F401


# 创建 FastAPI 应用实例
app = FastAPI(
    title="RAG Service",
    description="AI Agent后端服务",
    version="1.0.0",
    # Swagger UI 地址，浏览器打开可调试接口：http://host:port/docs
    docs_url="/docs",
    # ReDoc 文档地址，另一种接口文档风格：http://host:port/redoc
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(router)

"""====================rag 向量索引构建====================="""
#  fastapi服务初始化时执行一次回调
@app.on_event("startup")
async def startup():
    """应用启动时要执行的逻辑（每个 worker 进程会跑一次）。
    这里用 async def 是 FastAPI 事件钩子的写法；函数体内若没有 await，本质上仍会在事件循环里调度执行。
    """
    Base.metadata.create_all(bind=engine)
    try:
        if not check_index():
            logger.warning("向量索引不存在，重新构建")
            build_index()
            logger.info("向量索引构建完成")
    except Exception as exc:
        logger.warning("向量索引自动构建失败（可能模型未加载）：%s", exc)


if __name__ == "__main__":
    # 只有「直接 python main.py」运行本文件时才会进入这里；
    # 若用 `uvicorn main:app` 命令启动，则不会走这一段（由命令行参数决定）。
    uvicorn.run(
        # 字符串 "main:app"：表示「当前包里的 main 模块中的 app 变量」。
        # reload=True 时 Uvicorn 需要用字符串形式才能自动重载代码。
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        # Uvicorn 日志级别用小写：debug / info / warning / error
        log_level="info",
    )

