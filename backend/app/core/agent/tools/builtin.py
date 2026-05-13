from app.core.agent.tools.registry import ToolRegistry

registry = ToolRegistry.get_instance()

# ── 定义注册内置工具 ──────────────────────────────────────
# 在定义工具函数的同时，把这个函数自动注册到工具注册表里。
@registry.register(
  name="web_search",
  description="搜索互联网信息。参数: {\"query\": \"搜索关键词\"}",
  timeout=15.0,
  max_retry=1,
)
async def web_search(query: str) -> str:
    pass


@registry.register(
  name="calculator",
  description="数学计算。参数: {\"expression\": \"数学表达式，如 '2 + 3 * 4'\"}",
  timeout=5.0,
  max_retry=1,
)
async def calculator(expression: str) -> str:
    pass

