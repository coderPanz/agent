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
| `Agent第一版重构需求与目录方案.md` | 第一版 prompt，描述整体需求和流程设计 |
| `Agent第二版工程化技术方案.md` | **核心参考文档**，包含完整架构设计 + 14 章代码示例（2026-05-11 生成） |
| `Agent第三版落地实现与SSE方案.md` | **落地记录**，覆盖新增节点、Bug 修复清单、SSE 监控流设计、前端接入示例（2026-05-15 生成） |
| `Agent天气查询工具实现方案.md` | 工具能力扩展示例，包含 WeatherService、tool 注册、API 接入、测试方案（2026-05-16 新增） |
| `LangGraph入门与状态图示例.md` | LangGraph 概念学习笔记（含 MVP 代码模板） |
| `Agent执行流程与第一版范围.md` | 第一版流程图设计 |

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

### 工具系统架构（已完成重组）

| 文件 | 状态 | 说明 |
|------|------|------|
| `tools/registry.py` | ✅ 已实现 | ToolRegistry 单例，装饰器注册，asyncio.wait_for 超时+重试 |
| `tools/schema.py` | ✅ 已实现 | ToolResult Pydantic 模型 |
| `tools/builtin.py` | ✅ 已实现 | 工具装饰器注册点，weather_query/web_search/calculator |
| `tools/models/__init__.py` | ✅ 已实现（新增） | 工具实现层导出 |
| `tools/models/weather.py` | ✅ 已实现 | WeatherService 纯高德 API 实现，去掉 mock/openweather |

### API 层（已接入）

| 文件 | 状态 | 说明 |
|------|------|------|
| `app/api/routes.py` | ✅ 已实现 | `POST /api/agent_chat`（异步）+ `POST /api/agent/stream`（SSE 监控，修复了前缀） |
| `app/api/schemas.py` | ✅ 已实现 | `AgentChatRequest/Response` + `AgentStreamRequest` |
| `app/main.py` | ✅ 已修复 | 路由挂载添加 `/api` 前缀 |

### 前端（已接入）

| 文件 | 状态 | 说明 |
|------|------|------|
| `frontend/src/api/client.ts` | ✅ 已实现 | `AgentEvent` 联合类型 + `agentStream()` 异步生成器（SSE 解析） |
| `frontend/src/api/client.ts` | ✅ 已更新 | 新增 `ReActStep` / `ToolDetail` 类型；`node_done` 携带 `elapsed_ms` / `steps` / `tool_details` |
| `frontend/src/pages/Chat.tsx` | ✅ 已重构 | 可展开 `ExecutionCard`：默认显示节点名+耗时，展开后显示思考/调用/结果；去掉独立 tool_call 卡片 |
| `frontend/src/styles/chat.css` | ✅ 已重构 | 新增 exec-card / exec-timeline / react-step / step-box 等样式；保留 Markdown 样式 |
| `frontend/vite.config.ts` | ✅ 已修复 | 代理端口 8000，去掉 rewrite 保留 /api 前缀 |

### 服务层变更

| 文件 | 变更 |
|------|------|
| `app/services/llm.py` | 从 `openai.OpenAI` 改为 `langchain_openai.ChatOpenAI`，支持 `ainvoke` |
| `app/services/agent.py` | 已清空旧代码（原引用已删除模块），路由直接使用 `_runtime` 单例 |

### 工具能力实现状态

| 工具 | 路径 | 状态 | 说明 |
|------|------|------|------|
| `weather_query` | `tools/models/weather.py` | ✅ 已实现 | WeatherService 纯高德 API，GAODE_API_KEY 读取 .env，已线上验证 |
| `web_search` | `tools/builtin.py` | ⏳ 待接入 | 已注册骨架，需调用 Tavily API 或类似搜索引擎 |
| `calculator` | `tools/builtin.py` | ⏳ 待接入 | 已注册骨架，可用 `eval()` 或 `sympy` 安全计算 |

### 待实现（架构层 - P2）

| 文件 | 说明 |
|------|------|
| `memory/long_term.py` | 长期记忆（预留） |
| `executors/base.py` | 执行器抽象基类 |

### 已删除（第一版旧文件）

`agent.py`、`context.py`、`router.py`（根目录）、`memory.py`（根目录）、`trace.py`（根目录）、`tools.py`

## 当前开发阶段

**全栈可用**：前端 → SSE → Agent → LLM，进度卡片实时渲染 + Markdown 格式输出。

### 已验证通过的测试场景

| 场景 | 输入示例 | 执行链路 | 状态 |
|------|---------|--------|------|
| 简单对话 | "你好" / "你是谁？" | chat 意图 → chat_node → 答案 | ✅ 可用 |
| ReAct 循环 | "计算 123 × 456" | react 意图 → context_builder → react_executor → answer | ✅ 可用 |
| 天气查询（工具调用） | "北京明天天气如何" | react 意图 → tool_call (weather_query) → 天气结果 | ✅ 已实现 |
| 前端执行卡片 | 任意 react 意图 | 可展开卡片：耗时 + 思考/调用/结果步骤详情 | ✅ 可用 |
| SSE 事件流 | 通过 `/api/agent/stream` 端点 | start → node_done(with steps+timing) → answer → done | ✅ 可用 |

### 工具扩展模式（已验证）

**实现步骤**：
1. 在 `tools/models/` 创建服务类（如 `weather.py` 中的 `WeatherService`）
2. 在 `tools/models/__init__.py` 导出服务类
3. 在 `tools/builtin.py` 中用 `@registry.register()` 装饰异步函数
4. LLM 自动识别意图并调用，ReAct Executor 处理工具结果

**天气工具已完成实现**：
- ✅ `tools/models/weather.py` — WeatherService 纯高德 API，读取 `GAODE_API_KEY`
- ✅ `tools/builtin.py` — `weather_query()` 工具函数注册，格式化高德字段（白天/夜间/风力级）
- ✅ `agent_runtime.py` — 补充 `import app.core.agent.tools.builtin`，确保工具装饰器执行
- ✅ `frontend/vite.config.ts` — 去掉 rewrite，/api 前缀完整转发后端
- ✅ 端到端验证 — "北京明天天气如何" 返回真实高德数据（大雨 18-21°C 东风1-3级）

### 下一步工作优先级

| 优先级 | 任务 | 状态 | 说明 |
|--------|------|------|------|
| **P1** | 接入 web_search 工具 | ⏳ 待实现 | 调用 Tavily / SerpAPI，参考 weather 模式实现 |
| **P1** | 接入 calculator 工具 | ⏳ 待实现 | 用 `eval()` 或 `sympy`，参考 weather 模式实现 |
| **P2** | 长期记忆（`memory/long_term.py`） | ⏳ 待实现 | 向量数据库 + 语义检索 |
| **P2** | 进度卡片交互 | ⏳ 待实现 | 可折叠展开、显示工具调用明细 |
| **P3** | 天气工具扩展 | ✅ 已完成 | 已使用高德 API，真实数据验证通过 |
| **P3** | 多 Agent 编排 | ⏳ 待实现 | LangGraph Supervisor 模式 |

**工具扩展参考**：
- 新工具应按 weather 工具的模式组织（服务类 → models 层 → builtin 注册）
- 所有工具自动注入 LLM Prompt，支持 ReAct 循环调用

## 最近更新（2026-05-16）

| 改动 | 详情 |
|------|------|
| 工具架构重组 | 新增 `tools/models/` 层，天气工具完整实现并验证通过 |
| 天气工具实现 | WeatherService 支持 Mock 和 OpenWeather API，已在 ReAct 循环中验证 |
| 路由前缀修复 | API 端点改为 `/api/agent/stream`，与前端代理配置对齐 |
| 测试通过 | 测试语句"北京明天天气如何"能正确触发工具调用和完整执行流程 |

**工具实现验证结果**：
```
curl -X POST 'http://localhost:8000/api/agent/stream' \
  -H 'Content-Type: application/json' \
  -d '{"query":"北京明天天气如何","session_id":null}'

✅ 完整流程：start → router(react) → context_builder → react_executor(tool_call weather_query) 
→ answer(天气信息) → critic → memory_write → done
```

**How to apply:** 所有节点签名统一为 `async def xxx_node(state: AgentState) -> dict:`；LLM 客户端统一用 `init_llm_client()` 获取 ChatOpenAI 实例；所有工具通过 `@registry.register()` 装饰器注册到 `tools/builtin.py`，实现类放在 `tools/models/` 层。
