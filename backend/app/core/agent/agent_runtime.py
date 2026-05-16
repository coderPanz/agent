"""Agent-Runtime: 入口、流式输出、异常恢复、生命周期"""

import time
import uuid
from typing import AsyncIterator, AsyncGenerator
from langchain_core.messages import HumanMessage
from app.core.agent.state import AgentState, TokenUsage
from app.core.agent.graph import compile_graph
from app.core.agent.observability.trace import Tracer
import app.core.agent.tools.builtin  # noqa: F401 — 触发工具注册装饰器


class AgentRuntime:
    """
    Agent 运行时：对外暴露 chat() 和 stream_chat() 两个接口。
    """
    def __init__(self):
        self._graph = compile_graph()
    
    def _build_initial_state(self, query: str, session_id: str, user_id: str = "") -> AgentState:
        """构建初始 State"""
        return AgentState(
            messages = [HumanMessage(content=query)],
            session_id=session_id,
            user_id=user_id,
            token_usage=TokenUsage(budget=8192),
        )
    
    async def chat(self, query: str, session_id: str | None, user_id: str = "") -> str:
        """
        同步聊天接口：等待完整回复后返回字符串。
        """
        session_id = session_id or str(uuid.uuid4())
        tracer = Tracer(session_id=session_id)

        initial_state = self._build_initial_state(query, session_id, user_id)
        config = {"configurable": {"thread_id": session_id}}

        try:
            await tracer.log_node("runtime", "start", query_len=len(query))
            result = await self._graph.ainvoke(initial_state, config = config)
            await tracer.log_node("runtime", "end")
            return result["final_answer"] or result["messages"][-1].content
        except Exception as e:
            await tracer.log_error(-1, str(e))
            return f"抱歉，处理请求时遇到错误：{e}"


    async def stream_chat(self, query: str, session_id: str | None, user_id: str = "") -> AsyncIterator[str]:
        """
        流式聊天接口：逐步 yield token（适合 SSE / WebSocket 推送）。
        """
        session_id = session_id or str(uuid.uuid4())
        initial_state = self._build_initial_state(query, session_id, user_id)
        config = {"configurable": {"thread_id": session_id}}
        
        # LangGraph 的 astream 会在每个节点完成时 yield 状态快照
        # yield 暂停函数执行，返回当前值，等待下次调用继续执行
        yielded = False
        async for chunk in self._graph.astream(initial_state, config=config, stream_mode="values"):
            if not yielded and chunk.get("final_answer"):
                yield chunk["final_answer"]
                yielded = True

    async def stream_events(
        self, query: str, session_id: str | None, user_id: str = ""
    ) -> AsyncGenerator[dict, None]:
        """
        细粒度事件流，推送节点进度 + 工具调用 + 最终回答。
        前端通过 SSE 消费，用于渲染监控面板。

        事件类型：
          start      — 开始处理，携带 session_id
          node_done  — 某节点执行完毕，detail 字段补充摘要
          tool_call  — react_executor 完成后的工具调用汇总
          answer     — 最终回答（完整文本）
          error      — 运行时异常
          done       — 流结束
        """
        session_id = session_id or str(uuid.uuid4())
        initial_state = self._build_initial_state(query, session_id, user_id)
        config = {"configurable": {"thread_id": session_id}}

        NODE_LABELS: dict[str, str] = {
            "router":          "意图识别",
            "chat":            "生成回答",
            "context_builder": "构建上下文",
            "react_executor":  "思考推理",
            "critic":          "质量检验",
            "memory_write":    "记忆更新",
        }

        answer_sent = False
        prev_time = time.monotonic()

        try:
            yield {"type": "start", "session_id": session_id}

            async for chunk in self._graph.astream(
                initial_state, config=config, stream_mode="updates"
            ):
                now = time.monotonic()
                elapsed_ms = int((now - prev_time) * 1000)
                prev_time = now

                # chunk = {node_name: node_output_dict}
                for node_name, node_output in chunk.items():
                    if node_name not in NODE_LABELS:
                        continue

                    label = NODE_LABELS[node_name]

                    if node_name == "router":
                        yield {
                            "type": "node_done",
                            "name": node_name,
                            "label": label,
                            "detail": node_output.get("intent", "unknown"),
                            "elapsed_ms": elapsed_ms,
                        }

                    elif node_name == "react_executor":
                        react_steps = node_output.get("react_steps") or []
                        tool_calls  = node_output.get("tool_calls")  or []

                        steps_data = [
                            {
                                "step":        s.step        if hasattr(s, "step")        else s.get("step", 0),
                                "thought":     s.thought     if hasattr(s, "thought")     else s.get("thought", ""),
                                "action":      s.action      if hasattr(s, "action")      else s.get("action"),
                                "observation": (s.observation if hasattr(s, "observation") else s.get("observation")) or "",
                            }
                            for s in react_steps
                        ]

                        tool_details = [
                            {
                                "tool_name":  tc.tool_name  if hasattr(tc, "tool_name")  else tc.get("tool_name", ""),
                                "input":      tc.input      if hasattr(tc, "input")      else tc.get("input", {}),
                                "output":     tc.output     if hasattr(tc, "output")     else tc.get("output", ""),
                                "elapsed_ms": tc.elapsed_ms if hasattr(tc, "elapsed_ms") else tc.get("elapsed_ms", 0),
                            }
                            for tc in tool_calls
                        ]

                        yield {
                            "type":         "node_done",
                            "name":         node_name,
                            "label":        label,
                            "detail":       f"{len(react_steps)} 步推理",
                            "elapsed_ms":   elapsed_ms,
                            "steps":        steps_data,
                            "tool_details": tool_details,
                        }

                        final_answer = node_output.get("final_answer", "")
                        if final_answer and not answer_sent:
                            yield {"type": "answer", "content": final_answer}
                            answer_sent = True

                    elif node_name == "chat":
                        final_answer = node_output.get("final_answer", "")
                        if final_answer and not answer_sent:
                            yield {"type": "answer", "content": final_answer}
                            answer_sent = True
                        yield {"type": "node_done", "name": node_name, "label": label, "elapsed_ms": elapsed_ms}

                    else:
                        yield {"type": "node_done", "name": node_name, "label": label, "elapsed_ms": elapsed_ms}

            yield {"type": "done"}

        except Exception as e:
            yield {"type": "error", "content": str(e)}
            yield {"type": "done"}






