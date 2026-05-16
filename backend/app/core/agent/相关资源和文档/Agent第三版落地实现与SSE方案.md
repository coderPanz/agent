# Agent 第三版实现细节方案

> 在第二版技术方案的基础上，本文档记录从「代码骨架」到「完整可运行系统」的落地过程。  
> 覆盖：缺失节点的实现、Bug 修复清单、SSE 监控流设计、前端接入示例。

---

## 目录

1. [本版本变更总览](#1-本版本变更总览)
2. [新增节点实现](#2-新增节点实现)
3. [Graph 路由调整](#3-graph-路由调整)
4. [LLM 客户端切换](#4-llm-客户端切换)
5. [AgentRuntime 完整接口](#5-agentruntime-完整接口)
6. [SSE 监控流设计](#6-sse-监控流设计)
7. [API 层接入](#7-api-层接入)
8. [Bug 修复清单](#8-bug-修复清单)
9. [完整执行流程](#9-完整执行流程)
10. [前端接入示例](#10-前端接入示例)

---

## 1. 本版本变更总览

| 类别 | 文件 | 变更说明 |
|------|------|---------|
| 新增节点 | `nodes/chat.py` | 普通对话执行节点 |
| 新增节点 | `nodes/finalize.py` | 最终回答格式化节点 |
| 新增节点 | `nodes/memory_write.py` | 对话记忆写回节点 |
| 新增节点 | `nodes/human_approval.py` | Human-in-the-loop 审批节点（占位） |
| 节点实现 | `nodes/critic.py` | 填充质量检验逻辑 |
| Runtime | `agent_runtime.py` | 新增 `stream_events()` SSE 监控流接口 |
| Graph | `graph.py` | 引入 `chat` 节点，修复路由与编译函数 |
| LLM | `app/services/llm.py` | 从 `openai.OpenAI` 换成 `ChatOpenAI` |
| API | `app/api/routes.py` | 新增 `POST /agent/stream` SSE 端点 |
| API | `app/api/schemas.py` | 新增 `AgentStreamRequest` |
| Bug 修复 | 多文件 | 共 13 处语法/逻辑错误（见第 8 节） |

---

## 2. 新增节点实现

所有节点签名统一为：

```python
async def xxx_node(state: AgentState) -> dict:
    ...
```

节点只读 `state`，只写返回的 `dict`（LangGraph 自动 merge 进 AgentState）。

---

### 2.1 chat_node — 普通对话节点

**触发条件**：`router` 识别出 `intent = "chat"` 或 `"unknown"`

```python
# nodes/chat.py
from langchain_core.messages import AIMessage
from app.core.agent.state import AgentState
from app.services.llm import init_llm_client

async def chat_node(state: AgentState) -> dict:
    llm = init_llm_client()
    resp = await llm.ainvoke(state.messages)   # 直接把对话历史送给 LLM
    return {
        "final_answer": resp.content,
        "messages": [AIMessage(content=resp.content)],
    }
```

**设计要点**：
- 把整段 `state.messages` 传给 LLM，保留多轮上下文
- 同时写回 `messages`，让 LangGraph 的 `add_messages` reducer 追加历史

---

### 2.2 finalize_node — 最终回答格式化节点

**触发条件**：所有路径的最后一步，紧接 `chat` / `critic`

```python
# nodes/finalize.py
from langchain_core.messages import AIMessage
from app.core.agent.state import AgentState

async def finalize_node(state: AgentState) -> dict:
    if state.final_answer:
        return {"messages": [AIMessage(content=state.final_answer)]}

    # chat 路径兜底：从消息历史里找最后一条 AI 消息
    for msg in reversed(state.messages):
        if msg.type == "ai":
            return {"final_answer": msg.content, "messages": []}
    return {}
```

**设计要点**：
- `react` 路径：`final_answer` 已由 `react_executor` 填充，直接追加到消息历史
- `chat` 路径兜底：万一 `final_answer` 为空（异常情况），从历史反查

---

### 2.3 memory_write_node — 记忆写回节点

**触发条件**：`finalize` 之后，图的最终步骤

```python
# nodes/memory_write.py
from app.core.agent.state import AgentState
from app.core.agent.memory.manager import MemoryManager

async def memory_write_node(state: AgentState) -> dict:
    user_msg = ""
    for msg in reversed(state.messages):
        if msg.type == "human":
            user_msg = msg.content
            break

    if user_msg and state.final_answer:
        mgr = MemoryManager(session_id=state.session_id)
        await mgr.write_turn(user_msg, state.final_answer)

    return {}
```

**设计要点**：
- 从 `messages` 反向查找最后一条用户消息（不依赖固定下标，更健壮）
- 只在 `final_answer` 非空时写入，避免错误情况污染记忆

---

### 2.4 critic_node — 质量检验节点

**触发条件**：`react_executor` 完成后

```python
# nodes/critic.py
from app.core.agent.state import AgentState

async def critic_node(state: AgentState) -> dict:
    answer = state.final_answer.strip()
    if not answer or answer.startswith("抱歉，处理请求时遇到错误"):
        return {
            "critic_passed": False,
            "critic_feedback": "回答为空或包含错误，需要重试",
            "retry_count": state.retry_count + 1,
        }
    return {"critic_passed": True, "critic_feedback": ""}
```

**Critic 路由逻辑**（在 `graph.py` 中）：

```python
def _route_after_critic(state: AgentState) -> str:
    # 未通过且未超重试上限 → 回到 react_executor 重试
    if state.critic_passed is False and state.retry_count < state.max_retries:
        return "react_executor"
    return "finalize"
```

---

### 2.5 human_approval_node — 审批节点（占位）

```python
# nodes/human_approval.py
async def human_approval_node(state: AgentState) -> dict:
    """
    LangGraph 在此节点 interrupt，前端/管理员注入 human_approved=True/False 后恢复。
    生产接入方式：graph.compile(interrupt_before=["human_approval"])
    """
    return {}
```

---

## 3. Graph 路由调整

### 3.1 完整节点拓扑

```
START
  │
  ▼
[router]
  │ intent = "react"/"rag"      │ intent = "chat"/"unknown"
  ▼                              ▼
[context_builder]             [chat] ──────────────────┐
  │                                                     │
  ▼                                                     │
[react_executor] ←──── 重试 ────┐                      │
  │                              │                      │
  ▼                              │                      │
[critic] ──── 未通过 ────────────┘                      │
  │ 通过                                                │
  ▼                                                     │
[finalize] ◄────────────────────────────────────────────┘
  │
  ▼
[memory_write]  (use_human_approval=False)
  │
  ▼
END

── 或 ──

[finalize] → [human_approval] → [memory_write] → END  (use_human_approval=True)
                    │
                    └──── human_approved=False ──→ END
```

### 3.2 条件路由函数

```python
def _route_after_router(state: AgentState) -> str:
    if state.intent in ("react", "rag"):
        return "context_builder"
    return "chat"               # chat / unknown 走普通对话分支

def _route_after_critic(state: AgentState) -> str:
    if state.critic_passed is False and state.retry_count < state.max_retries:
        return "react_executor"
    return "finalize"
```

### 3.3 compile_graph 修复

```python
def compile_graph(use_human_approval: bool = False, checkpointer=None):
    builder = build_graph(use_human_approval)   # 传入参数
    cp = checkpointer or MemorySaver()           # 默认内存 checkpointer
    return builder.compile(checkpointer=cp)
```

---

## 4. LLM 客户端切换

**问题**：原代码使用 `openai.OpenAI`（同步客户端），不支持 `await llm.ainvoke()`。

**修复**：换成 `langchain_openai.ChatOpenAI`，与 LangChain 生态完全兼容。

```python
# app/services/llm.py
from langchain_openai import ChatOpenAI

_llm_client = None

def init_llm_client():
    global _llm_client
    if not _llm_client:
        _llm_client = ChatOpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        )
    return _llm_client
```

**为什么用 `ChatOpenAI` 而不是 `openai.AsyncOpenAI`？**

| | `openai.AsyncOpenAI` | `langchain_openai.ChatOpenAI` |
|-|---------------------|-------------------------------|
| `ainvoke()` | ✗ 没有 | ✅ 原生支持 |
| 传 `list[BaseMessage]` | ✗ 需手动转换 | ✅ 直接传 |
| LangGraph 事件流集成 | ✗ 需自实现 | ✅ 自动 emit events |
| Callback 系统 | ✗ | ✅ |

---

## 5. AgentRuntime 完整接口

```python
class AgentRuntime:
    def __init__(self): ...

    async def chat(query, session_id, user_id="") -> str
    # 等待完整回复，适合普通 REST 接口

    async def stream_chat(query, session_id, user_id="") -> AsyncIterator[str]
    # 流式回复 token，适合 WebSocket 或简单 SSE

    async def stream_events(query, session_id, user_id="") -> AsyncGenerator[dict, None]
    # 结构化进度事件流，适合前端监控面板（见第 6 节）
```

---

## 6. SSE 监控流设计

### 6.1 为什么用 SSE

| | HTTP 轮询 | WebSocket | SSE |
|-|-----------|-----------|-----|
| 实现复杂度 | 低 | 高 | 低 |
| 服务器推送 | ✗（客户端拉） | ✅ | ✅ |
| 单向/双向 | — | 双向 | 单向（服务器→客户端） |
| 适合场景 | 低频状态查询 | 实时双工 | 进度推送 ✅ |

Agent 执行过程是典型的「服务器单向推送」场景，SSE 是最合适的选择。

### 6.2 事件类型定义

| `type` | 触发时机 | 附带字段 |
|--------|---------|---------|
| `start` | 开始处理 | `session_id` |
| `node_done` | 某节点执行完毕 | `name`, `label`, `detail` |
| `tool_call` | react_executor 完成工具调用 | `tools`（各工具调用次数），`total` |
| `answer` | 最终回答生成完毕 | `content` |
| `error` | 运行时异常 | `content`（错误信息） |
| `done` | 流结束 | — |

### 6.3 典型事件序列

**普通对话（chat 意图）：**
```
{"type": "start",     "session_id": "abc123"}
{"type": "node_done", "name": "router",       "label": "意图识别",   "detail": "chat"}
{"type": "answer",    "content": "你好，我是..."}
{"type": "node_done", "name": "chat",         "label": "生成回答"}
{"type": "node_done", "name": "memory_write", "label": "记忆更新"}
{"type": "done"}
```

**工具调用（react 意图）：**
```
{"type": "start",     "session_id": "def456"}
{"type": "node_done", "name": "router",          "label": "意图识别",   "detail": "react"}
{"type": "node_done", "name": "context_builder", "label": "构建上下文"}
{"type": "tool_call", "tools": {"web_search": 3}, "total": 3}
{"type": "node_done", "name": "react_executor",  "label": "思考推理",   "detail": "2 步推理"}
{"type": "node_done", "name": "critic",          "label": "质量检验"}
{"type": "answer",    "content": "LangGraph 最新版本是..."}
{"type": "node_done", "name": "finalize",        "label": "最终回答"}
{"type": "node_done", "name": "memory_write",    "label": "记忆更新"}
{"type": "done"}
```

### 6.4 stream_events 核心实现

```python
async def stream_events(self, query, session_id, user_id=""):
    session_id = session_id or str(uuid.uuid4())
    initial_state = self._build_initial_state(query, session_id, user_id)
    config = {"configurable": {"thread_id": session_id}}

    NODE_LABELS = {
        "router":          "意图识别",
        "chat":            "生成回答",
        "context_builder": "构建上下文",
        "react_executor":  "思考推理",
        "critic":          "质量检验",
        "memory_write":    "记忆更新",
    }

    answer_sent = False
    yield {"type": "start", "session_id": session_id}

    async for chunk in self._graph.astream(
        initial_state, config=config, stream_mode="updates"
    ):
        # stream_mode="updates" 每个 chunk = {节点名: 该节点的返回 dict}
        for node_name, node_output in chunk.items():
            if node_name not in NODE_LABELS:
                continue
            ...
    yield {"type": "done"}
```

**为什么用 `stream_mode="updates"` 而不是 `astream_events`？**

- `stream_mode="updates"` 直接拿到每个节点的**返回值**（Python dict），可以直接读 `tool_calls`、`react_steps`、`final_answer` 字段
- `astream_events` 适合需要监听 LLM **token 级别**流式输出的场景，但需要额外过滤和解析
- 本版本优先实现节点级别监控，token 级别可按需升级

---

## 7. API 层接入

### 7.1 SSE 端点

```python
# app/api/routes.py
from fastapi.responses import StreamingResponse
import json

_runtime = AgentRuntime()   # 模块级单例，避免每次请求重新编译 Graph

@router.post("/agent/stream", tags=["agent"])
async def agent_stream(request: AgentStreamRequest) -> StreamingResponse:
    async def event_generator():
        async for evt in _runtime.stream_events(
            request.query, request.session_id, request.user_id
        ):
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",    # 禁用 nginx 缓冲，保证实时推送
        },
    )
```

**为什么用 POST 而不是 GET？**

- query 可能很长，URL 长度有上限（~2000 字符）
- POST body 无限制，且支持 JSON 格式传参（session_id、user_id 等）

### 7.2 请求/响应 Schema

```python
class AgentStreamRequest(BaseModel):
    query: str
    session_id: str | None = None   # 不传则后端自动生成 UUID
    user_id: str = ""

# 响应：text/event-stream，每行格式：
# data: {"type": "...", ...}\n\n
```

### 7.3 现有接口对比

| 接口 | 方法 | 用途 | 适合场景 |
|------|------|------|---------|
| `/agent_chat` | POST | 等待完整回复 | 简单集成、非实时场景 |
| `/agent/stream` | POST | SSE 事件流 | 前端监控面板、流式展示 |

---

## 8. Bug 修复清单

| 文件 | 行 | 错误类型 | 原代码 | 修复 |
|------|-----|---------|--------|------|
| `agent_runtime.py` | 19 | 语法错误 | `-> AgentState` | `-> AgentState:` |
| `agent_runtime.py` | 40 | 拼写错误 | `awiat self._graph...` | `await self._graph...` |
| `agent_runtime.py` | 44 | 语法+名称 | `awiat tracer.log=log_error(...)` | `await tracer.log_error(...)` |
| `state.py` | 17 | `__future__` 位置错误 | 注释块在 import 前 | 移动到文件首行 |
| `graph.py` | 34 | 语法错误 | `bool: False` | `bool = False` |
| `graph.py` | 87-91 | 未定义变量 | `-> CompiledGraph`，`checkpointer` 未定义 | 移除类型注解，加参数 |
| `executor.py` | 48 | 变量名错误 | `thought.group(1)` | `thought_match.group(1)` |
| `executor.py` | 51 | 逻辑错误 | 总是设置 `final_answer=""`，导致循环提前退出 | 只在匹配时才设置 |
| `executor.py` | 71 | 类名错误 | `ToolCallRecord.get_instance()` | `ToolRegistry.get_instance()` |
| `executor.py` | 91-92 | 语法错误 | `react_steps = list[ReActStep] = []` | `react_steps: list[ReActStep] = []` |
| `executor.py` | 170-178 | 缩进错误 | 6 空格（无效层级） | 4 空格（函数体层级） |
| `router.py` | 3 | 模块名错误 | `langchain_core.message` | `langchain_core.messages` |
| `context_builder.py` | 23,25,53,59 | 多处错误 | `langchain_core.message`、`MemorySaver`、`state.message`、`state.token_usage_budget` | 逐一修正 |

---

## 9. 完整执行流程

以「帮我搜索 LangGraph 最新版本」为例（react 意图）：

```
1. AgentRuntime.chat("帮我搜索...", session_id="s1")
   └─ _build_initial_state() → AgentState(messages=[HumanMessage], session_id="s1")

2. graph.ainvoke(state)
   │
   ├─ router_node(state)
   │   ├─ LLM 识别意图 → "react"
   │   └─ 返回 {"intent": "react"}
   │
   ├─ context_builder_node(state)
   │   ├─ MemoryManager.get_summary() → "" (首次对话)
   │   ├─ 格式化最近 8 轮对话
   │   └─ 返回 {"context_str": "...", "memory_summary": ""}
   │
   ├─ react_executor_node(state)
   │   ├─ 构建 system_prompt（含工具描述）
   │   ├─ Step 0: LLM → Thought + Final Answer（无可用工具时直接回答）
   │   └─ 返回 {"final_answer": "...", "react_steps": [...], "tool_calls": []}
   │
   ├─ critic_node(state)
   │   ├─ final_answer 非空 → critic_passed=True
   │   └─ 返回 {"critic_passed": True}
   │
   ├─ finalize_node(state)
   │   └─ 返回 {"messages": [AIMessage(content=final_answer)]}
   │
   └─ memory_write_node(state)
       ├─ MemoryManager.write_turn(user_msg, final_answer)
       └─ 返回 {}

3. AgentRuntime 返回 result["final_answer"]
```

---

## 10. 前端接入示例

### 10.1 原生 EventSource（GET 方式）

> 注意：原生 `EventSource` 只支持 GET，不支持 POST 请求体。  
> 如需传 `session_id` 等参数，改用 `fetch` + `ReadableStream`（见 10.2）。

```javascript
const source = new EventSource('/agent/stream?query=你好');

source.onmessage = ({ data }) => {
  const evt = JSON.parse(data);
  handleEvent(evt);
};

source.onerror = () => source.close();
```

### 10.2 fetch + ReadableStream（POST 方式，推荐）

```javascript
async function streamAgent(query, sessionId) {
  const res = await fetch('/agent/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id: sessionId }),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop();   // 保留未完整的最后一段

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const evt = JSON.parse(line.slice(6));
      handleEvent(evt);
    }
  }
}
```

### 10.3 事件处理（渲染监控面板）

```javascript
const progressCards = [];
let answer = '';

function handleEvent(evt) {
  switch (evt.type) {
    case 'start':
      console.log('Session:', evt.session_id);
      break;

    case 'node_done':
      // 渲染进度卡片：「意图识别 ✓」「思考推理 (2 步) ✓」
      progressCards.push({
        label:  evt.label,
        detail: evt.detail || '',
        done:   true,
      });
      renderProgress(progressCards);
      break;

    case 'tool_call':
      // 渲染工具调用卡片：「已调用工具 3 次 >」
      progressCards.push({
        label:  `已调用工具 ${evt.total} 次`,
        detail: Object.entries(evt.tools)
                  .map(([k, v]) => `${k} ×${v}`)
                  .join('、'),
        done:   true,
      });
      renderProgress(progressCards);
      break;

    case 'answer':
      // 显示最终回答
      answer = evt.content;
      renderAnswer(answer);
      break;

    case 'error':
      renderError(evt.content);
      break;

    case 'done':
      hideLoadingSpinner();
      break;
  }
}
```

### 10.4 Vue 组件伪代码

```vue
<template>
  <div class="agent-chat">
    <!-- 进度卡片列表 -->
    <div v-for="card in progressCards" class="progress-card">
      <span>{{ card.label }}</span>
      <span v-if="card.detail" class="detail">{{ card.detail }}</span>
      <span class="chevron">›</span>
    </div>

    <!-- 最终回答 -->
    <div v-if="answer" class="answer" v-html="renderMarkdown(answer)" />

    <!-- 加载中 -->
    <div v-if="loading" class="spinner">处理中...</div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const progressCards = ref([]);
const answer = ref('');
const loading = ref(false);

async function send(query) {
  progressCards.value = [];
  answer.value = '';
  loading.value = true;

  await streamAgent(query, null, (evt) => {
    if (evt.type === 'node_done' || evt.type === 'tool_call') {
      progressCards.value.push(/* ... */);
    } else if (evt.type === 'answer') {
      answer.value = evt.content;
    } else if (evt.type === 'done') {
      loading.value = false;
    }
  });
}
</script>
```

---

## 后续扩展方向

| 方向 | 当前状态 | 扩展方式 |
|------|---------|---------|
| Token 级别流式输出 | 节点级别 | 改用 `astream_events(version="v2")` 监听 `on_chat_model_stream` |
| 工具调用逐步推送 | 批量推送 | 在 `react_executor` 内部 yield 自定义事件 |
| Web Search 真实接入 | stub | `tools/builtin.py` 接入 Tavily / SerpAPI |
| 长期记忆 | 未实现 | `memory/long_term.py` + 向量数据库 |
| Human-in-the-loop | 占位节点 | `graph.compile(interrupt_before=["human_approval"])` |
| 多 Agent 编排 | 未实现 | LangGraph Multi-Agent Supervisor 模式 |
