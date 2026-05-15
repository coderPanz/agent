import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

from app.core.agent.agent_runtime import AgentRuntime

async def main():
    runtime = AgentRuntime()

    # ── 示例 1：普通对话 ──────────────────────────────────
    print("=== 普通对话 ===")
    answer = await runtime.chat(
        query="你好，介绍一下你自己",
        session_id="demo-session-001",
    )
    print(f"回答：{answer}\n")
    
    # ── 示例 2：工具调用（需要 web_search 工具已注册） ────
    print("=== 工具调用 ===")
    answer = await runtime.chat(
        query="帮我搜索一下 Python LangGraph 的最新版本",
        session_id="demo-session-002",
    )
    print(f"回答：{answer}\n")
    

    # ── 示例 3：流式输出 ──────────────────────────────────
    print("=== 流式输出 ===")
    async for chunk in runtime.stream_chat(
        query="用工具计算 123 * 456",
        session_id="demo-session-003",
    ):
        print(chunk, end="", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(main())