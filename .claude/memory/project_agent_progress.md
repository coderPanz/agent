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
| `第三版实现细节方案.md` | **落地记录**，覆盖新增节点、Bug 修复清单、SSE 监控流设计、前端接入示例（2026-05-15 生成） |
| `天气查询功能实现方案.md` | 工具能力扩展示例，包含 WeatherService、tool 注册、API 接入、测试方案（2026-05-16 新增） |
| `langgraph.md` | LangGraph 概念学习笔记（含 MVP 代码模板） |
| `agent 执行流程.md` | 第一版流程图设计 |

## 文件实现状态（截至 2026-05-15，commit 0c086f6）

### P0 已实现

| 文件 | 状态 | 说明 |
|------|------|------|
| `state.py` | ✅ 已实现 | AgentState、TokenUsage、ReActStep、ToolCallRecord 完整定义 |
| `graph.py` | ✅ 已实现 | StateGraph 节点注册 + 条件路由（含 chat_node 分支、human_approval 可选） |
| `agent_runtime.py` | ✅ 已实现 | chat() + stream_chat() + stream_events()（SSE 监控流，推送 start/node_done/tool_call/answer/done） |
| `executors/react/executor.py` | ✅ 已实现 | 手动 Thought→Action→Obs 循环，含 hallucination 防护和兜底 |
| `executors/react/prompts.py` | ✅ 已实现 | REACT_SYSTEM_PROMPT、OBSERVATION_TEMPLATE |
| `tools/schema.py` | ✅ 已实现 | ToolResult Pydantic 模型（tool_name/output/success/error/raw） |
| `tools/registry.py` | ✅ 已实现 | 单例 ToolRegistry，装饰器注册，asyncio.wait_for 超时，重试 |

### P1 已实现

| 文件 | 状态 | 说明 |
|------|------|------|
| `nodes/router.py` | ✅ 已实现 | LLM 意图分类，输出 react/chat/rag/unknown |
| `nodes/context_builder.py` | ✅ 已实现 | 优先级拼接，token 预算裁剪，最近 8 轮对话 |
| `nodes/chat.py` | ✅ 已实现（新增） | chat/unknown 意图直接调 LLM，写回 final_answer + messages |
| `nodes/critic.py` | ✅ 已实现 | 检查 final_answer 非空且非错误信息，不通过时 retry_count+1 |
| `nodes/finalize.py` | ✅ 已实现（新增） | 将 final_answer 追加到 messages；chat 路径从 messages 反向提取 |
| `nodes/memory_write.py` | ✅ 已实现（新增） | 调 MemoryManager.write_turn() 写入本轮对话 |
| `nodes/human_approval.py` | ✅ 已实现（新增） | HITL 占位节点，图在此 interrupt，恢复时注入 human_approved |
| `memory/short_term.py` | ✅ 已实现 | in-memory dict 存储，append/get_all/trim_if_needed，生产可换 Redis |
| `memory/summarizer.py` | ✅ 已实现 | LLM 对话历史压缩，2-3 句摘要 |
| `memory/manager.py` | ✅ 已实现 | MemoryManager 统一入口，write_turn/get_summary，超 20 轮自动压缩 |
| `observability/logger.py` | ✅ 已实现 | get_logger/log_json，结构化 JSON 格式输出 |
| `observability/callback_handler.py` | ✅ 已实现 | AgentCallbackHandler，监听 llm_start/end、tool_start/end |
| `observability/trace.py` | ✅ 已实现 | Tracer 类，log_step/log_node/log_token/log_error，依赖 logger |
| `executors/react/self_refine.py` | ✅ 已实现 | LLM 自我修正，PASS/REVISE 协议，最多 max_rounds 次迭代 |
| `tools/builtin.py` | ✅ 已实现（stub） | web_search / calculator 注册骨架，函数体待接入真实实现 |
| `demo.py` | ✅ 已实现（新增） | 端到端测试入口：普通对话 / 工具调用 / 流式输出三个示例，均已验证通过 |

### API 层（已接入）

| 文件 | 状态 | 说明 |
|------|------|------|
| `app/api/routes.py` | ✅ 已实现 | `POST /agent_chat`（异步）+ `POST /agent/stream`（SSE 监控） |
| `app/api/schemas.py` | ✅ 已实现 | `AgentChatRequest/Response` + `AgentStreamRequest` |

### 前端（已接入）

| 文件 | 状态 | 说明 |
|------|------|------|
| `frontend/src/api/client.ts` | ✅ 已实现 | `AgentEvent` 联合类型 + `agentStream()` 异步生成器（SSE 解析） |
| `frontend/src/pages/Chat.tsx` | ✅ 已实现（改进） | 集成 `react-markdown`；实时渲染进度卡片 + Markdown 格式答案 |
| `frontend/src/styles/chat.css` | ✅ 已实现（扩展） | `.progress-card` / `.progress-list` 样式 + Markdown 渲染样式（标题、列表、代码、表格等） |
| `frontend/vite.config.ts` | ✅ 已修复 | 代理端口从 8002 改为 8000，对接后端服务 |

### 服务层变更

| 文件 | 变更 |
|------|------|
| `app/services/llm.py` | 从 `openai.OpenAI` 改为 `langchain_openai.ChatOpenAI`，支持 `ainvoke` |
| `app/services/agent.py` | 已清空旧代码（原引用已删除模块），路由直接使用 `_runtime` 单例 |

### 待实现（P2）

| 文件 | 说明 |
|------|------|
| `memory/long_term.py` | 长期记忆（预留） |
| `executors/base.py` | 执行器抽象基类 |
| `tools/builtin.py` | web_search / calculator 接入真实实现 |

### 已删除（第一版旧文件）

`agent.py`、`context.py`、`router.py`（根目录）、`memory.py`（根目录）、`trace.py`（根目录）、`tools.py`

## 当前开发阶段

**全栈可用**：前端 → SSE → Agent → LLM，进度卡片实时渲染 + Markdown 格式输出。

### 已验证通过的测试场景

| 场景 | 输入示例 | 执行链路 | 状态 |
|------|---------|--------|------|
| 简单对话 | "你好" / "你是谁？" | chat 意图 → chat_node → 答案 | ✅ 可用 |
| ReAct 循环 | "计算 123 × 456" | react 意图 → context_builder → react_executor → answer | ✅ 可用 |
| 完整工具调用 | （工具函数需接入真实实现） | → tool_call 事件推送 | ⏳ 工具待接入 |
| 前端显示 | 任意输入 | Markdown 渲染 + 进度卡片 | ✅ 可用 |

### 工具扩展准备

已提供天气查询工具的完整实现文档（`天气查询功能实现方案.md`），用户可参考该文档实现以下工具：
- `weather_query(city, days)` — 天气查询（支持 Mock 和 OpenWeather API）
- 参考文档包含：工具服务层实现、tool 注册装饰器、测试用例、部署配置

**工具扩展模式**：
1. 创建服务模块 (`tools/xxxx.py`)
2. 在 `tools/builtin.py` 中用 `@registry.register()` 注册
3. LLM 自动识别意图并调用，ReAct Executor 处理工具结果

### 下一步工作优先级

| 优先级 | 任务 | 说明 |
|--------|------|------|
| **P1** | 实现天气查询工具 | 参考提供的实现文档，手动编码（预计 1-2 小时） |
| **P1** | 接入 web_search / calculator | 调用 Tavily API / eval()，接线到 `tools/builtin.py` |
| **P2** | 长期记忆（`memory/long_term.py`） | 向量数据库 + 语义检索 |
| **P2** | 进度卡片交互 | 可折叠展开、显示工具调用明细 |
| **P3** | 多 Agent 编排 | LangGraph Supervisor 模式 |

**How to apply:** 所有节点签名统一为 `async def xxx_node(state: AgentState) -> dict:`；LLM 客户端统一用 `init_llm_client()` 获取 ChatOpenAI 实例；所有工具通过 `@registry.register()` 装饰器注册。
