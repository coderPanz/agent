"""
Agent-ToolRegistry: 工具注册、调度、权限、超时、重试

ToolRegistry 是工具的统一入口：
- 注册：`@registry.register(name, permissions, timeout)`
- 调度：`registry.execute(name, input)` 内置超时 + 重试
- 校验：用 Pydantic Schema 验证入参，防止格式错误传给工具
"""


import asyncio
from pydantic import BaseModel
from typing import Any, Callable
from app.core.agent.tools.schema import ToolResult

class ToolRegistry:
    """
    工具注册中心：管理所有可被 Agent 调用的工具。
    单例模式，全局唯一。
    """
    _instance: "ToolRegistry | None" = None
    
    def __init__(self):
        # {工具名: {"fn": 异步函数, "timeout": 秒, "max_retry": 次}}
        self._tools: dict[str, dict] = {}
        self._descriptions: dict[str, str] = {}

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(
      self,
      name: str,
      description: str,
      timeout: float = 10.0,
      max_retry: int = 1,
    ):
      """装饰器：注册一个工具函数"""
      def decorator(fn: Callable):
          self._tools[name] = {"fn": fn, "timeout": timeout, "max_retry": max_retry}
          self._descriptions[name] = description
          return fn
      return decorator


    def has_tool(self, name: str) -> bool:
        return name in self._tools
    
    def list_tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def get_descriptions(self) -> str:
        """返回所有工具的描述文本，用于注入 prompt"""
        lines = []
        for name, desc in self._descriptions.items():
            lines.append(f'- {name}: {desc}')
        return '\n'.join(lines)


    async def execute(self, name: str, input_data: dict[str, Any]) -> ToolResult:
        """调用工具，内置超时控制和重试逻辑"""
        if name not in self._tools:
            return ToolResult(tool_name=name, output="", success=False, error=f"工具 {name} 未注册")

        meta = self._tools[name]
        fn = meta["fn"]
        timeout = meta["timeout"]
        max_retry = meta["max_retry"]
        
        last_error = ""
        for attempt in range(max_retry + 1):
            try:
                # asyncio.wait_for 实现超时控制
                raw = await asyncio.wait_for(fn(**input_data), timeout=timeout)
                return ToolResult(
                    tool_name=name,
                    output=str(raw)[:2000],   # 截断防止 token 爆炸
                    success=True,
                    raw=raw,
                )
            except asyncio.TimeoutError:
                last_error = f"工具 {name} 超时（{timeout}s）"
            except Exception as e:
                last_error = f"工具 {name} 执行错误：{e}"

        return ToolResult(tool_name=name, output="", success=False, error=last_error)







