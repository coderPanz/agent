---
name: Agent 模块开发进度
description: backend/app/core/agent/ 下各文件的实现状态，区分「已实现」与「仅占位/待实现」
type: project
originSessionId: f7f05be4-dddf-4c65-91a4-0fe439b4f10f
---
项目路径：`backend/app/core/agent/`

## 已有技术文档（参考设计）

| 文件 | 说明 |
|------|------|
| `第一版技术方案.md` | 第一版 prompt，描述整体需求和流程设计 |
| `第二版技术方案.md` | **核心参考文档**，包含完整架构设计 + 14 章代码示例（2026-05-11 生成） |
| `langgraph.md` | LangGraph 概念学习笔记（含 MVP 代码模板） |
| `agent 执行流程.md` | 第一版流程图设计 |

## 文件实现状态（截至 2026-05-13，commit e89c5e3）

### P0 已实现

| 文件 | 状态 | 说明 |
|------|------|------|
| `state.py` | ✅ 已实现 | AgentState、TokenUsage、ReActStep、ToolCallRecord 完整定义 |
| `graph.py` | ✅ 已实现 | StateGraph 节点注册 + 条件路由（含 human_approval 可选） |
| `agent_runtime.py` | ✅ 已实现 | chat() 同步 + stream_chat() 流式两个接口 |
| `executors/react/executor.py` | ✅ 已实现 | 手动 Thought→Action→Obs 循环，含 hallucination 防护和兜底 |
| `executors/react/prompts.py` | ✅ 已实现 | REACT_SYSTEM_PROMPT、OBSERVATION_TEMPLATE |
| `tools/schema.py` | ✅ 已实现 | ToolResult Pydantic 模型（tool_name/output/success/error/raw） |
| `tools/registry.py` | ✅ 已实现 | 单例 ToolRegistry，装饰器注册，asyncio.wait_for 超时，重试 |

### P1 已实现

| 文件 | 状态 | 说明 |
|------|------|------|
| `nodes/router.py` | ✅ 已实现 | LLM 意图分类，输出 react/chat/rag/unknown |
| `nodes/context_builder.py` | ✅ 已实现 | 优先级拼接，token 预算裁剪，最近 8 轮对话 |
| `nodes/critic.py` | ✅ 已实现 | LLM 质量校验，retry_count 超限时兜底通过 |
| `memory/short_term.py` | ✅ 已实现 | in-memory dict 存储，append/get_all/trim_if_needed，生产可换 Redis |
| `memory/summarizer.py` | ✅ 已实现 | LLM 对话历史压缩，2-3 句摘要 |
| `memory/manager.py` | ✅ 已实现 | MemoryManager 统一入口，write_turn/get_summary，超 20 轮自动压缩 |
| `observability/trace.py` | ✅ 已实现 | 结构化 JSON Trace，节点/工具/token/错误日志 |
| `executors/react/self_refine.py` | ✅ 已实现 | LLM 自我修正，PASS/REVISE 协议，最多 max_rounds 次迭代 |
| `tools/builtin.py` | ✅ 已实现（stub） | web_search / calculator 注册骨架，函数体待接入真实实现 |

### 待实现（P1/P2）

| 文件 | 说明 |
|------|------|
| `memory/long_term.py` | 长期记忆（预留） |
| `nodes/finalize.py` | 最终回复组装节点 |
| `nodes/memory_write.py` | 记忆写回节点 |
| `nodes/human_approval.py` | Human-in-the-loop 中断节点 |
| `observability/logger.py` | 日志封装 |
| `observability/callback_handler.py` | LangChain Callback 钩子 |
| `executors/base.py` | 执行器抽象基类 |

### 已删除（第一版旧文件）

`agent.py`、`context.py`、`router.py`（根目录）、`memory.py`（根目录）、`trace.py`（根目录）、`tools.py`

## 当前开发重点

memory 子模块已全部就绪，下一步补全剩余 graph 节点：
1. `nodes/finalize.py` + `nodes/memory_write.py`（graph 依赖）
2. `tools/builtin.py` 中 web_search / calculator 接入真实实现
3. `observability/logger.py` + `observability/callback_handler.py`（可选）

**How to apply:** 实现时对照 `第二版技术方案.md` 对应章节，所有节点签名统一为 `async def xxx_node(state: AgentState) -> dict:`。
