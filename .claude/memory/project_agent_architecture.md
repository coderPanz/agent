---
name: Agent 架构设计与执行流程
description: 完整的 Agent 系统架构图、模块职责、节点执行流程、数据流向，帮助快速理解全局设计
type: project
---

## 系统全景

```
用户请求
    │
    ▼
┌─────────────────────────────────────────────┐
│              Agent Runtime                  │  ← 生命周期 / 异常兜底 / 流式输出
│  ┌─────────────────────────────────────┐   │
│  │        LangGraph StateGraph          │   │
│  │                                     │   │
│  │  [Router] → [ContextBuilder]        │   │
│  │                  ↓                  │   │
│  │         [ReActExecutor]             │   │
│  │      (Thought→Action→Obs 循环)      │   │
│  │                  ↓                  │   │
│  │    [SelfRefine?] → [Critic?]        │   │
│  │                  ↓                  │   │
│  │  [Finalize] → [MemoryWrite]         │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
         │                    │
    ToolRegistry          MemoryManager
    (注册/调度/超时/重试)  (短期/摘要/长期)
```

---

## 节点职责表

| 节点 | 文件 | 输入 | 输出 | 职责 |
|------|------|------|------|------|
| router | `nodes/router.py` | messages[-1] | intent | LLM 分类意图：react / chat / rag / unknown |
| context_builder | `nodes/context_builder.py` | messages, rag_results | context_str, memory_summary | 按优先级拼装 Prompt 上下文，含 token 裁剪 |
| react_executor | `executors/react/executor.py` | context_str, messages | final_answer, react_steps, tool_calls | 手动实现 Thought→Action→Obs 循环 |
| critic | `nodes/critic.py` | final_answer, messages | critic_passed, critic_feedback | 质量校验；失败时触发重试 |
| finalize | `nodes/finalize.py` | final_answer | messages（最终） | 组装最终回复写入消息历史 |
| memory_write | `nodes/memory_write.py` | messages, session_id | — | 将本轮对话写回 MemoryManager |
| human_approval | `nodes/human_approval.py` | messages[-1] | human_approved | interrupt() 暂停等待人工决策 |

---

## 完整执行流程

```
用户输入
    │
    ▼
[1] AgentRuntime.chat(query)
    → 初始化 AgentState（messages, session_id, token_budget）
    → graph.ainvoke(state)
    │
    ▼
[2] router_node
    → LLM 单次调用，输出 JSON {"intent": "react|chat|rag|unknown"}
    → 写回 state.intent
    │
    ├─ intent = "chat" ──────────────────────────────┐
    │                                                 │
    ▼                                                 │
[3] context_builder_node                              │
    → memory_mgr.get_summary() 取历史摘要             │
    → 格式化最近 8 轮对话                             │
    → 按优先级拼接：任务目标 > 摘要 > RAG > 对话      │
    → 写回 state.context_str                          │
    │                                                 │
    ▼                                                 │
[4] react_executor_node（循环，最多 max_steps 步）    │
    → 构建 [SystemPrompt + context_str + messages]    │
    → LLM 输出 Thought + Action / Final Answer        │
    ├─ Final Answer → 退出循环                        │
    └─ Action:                                        │
        → 校验工具名（防 hallucination）               │
        → tool_registry.execute(name, input)          │
            ├─ asyncio.wait_for（超时控制）            │
            └─ 重试 max_retry 次                       │
        → 追加 Observation 到 history                 │
        → 记录 ReActStep 到 state.react_steps         │
    → 写回 state.final_answer, tool_calls             │
    │                                                 │
    ▼                                                 │
[5] critic_node                                       │
    → LLM 评估 final_answer 质量                      │
    ├─ pass=True  ──→ finalize                        │
    └─ pass=False ──→ react_executor（重试）           │
       (retry_count >= max_retries 时强制通过)         │
    │                                                 │
    ▼                                                 │
[6] finalize_node  ←────────────────────────────────┘
    → 将 final_answer 包装为 AIMessage
    → 写入 state.messages
    │
    ▼
[7] memory_write_node
    → memory_mgr.write_turn(user_msg, assistant_msg)
    → 超过 20 条时自动 summarize 压缩
    │
    ▼
[8] END → 返回 state.final_answer
```

---

## ReAct 内部循环细节

```
for step in range(max_steps):
    llm_response = await llm.ainvoke(history)
    parsed = _parse_llm_output(raw_text)
    │
    ├─ "final_answer" in parsed → return
    ├─ "action" not in parsed  → break（防死循环）
    └─ action found:
        ├─ registry.has_tool(name) == False
        │   → observation = "工具不存在" 错误信息（防 hallucination）
        └─ registry.has_tool(name) == True
            → await registry.execute(name, input)
            → 记录 ToolCallRecord（含耗时、是否成功）
    → history.append(AIMessage + HumanMessage(Observation))
    → react_steps.append(ReActStep)

超出 max_steps → 返回兜底回复
```

---

## Context Builder 优先级策略

```
Token Budget = state.token_usage.budget

拼接顺序（高优先级先写，低优先级可裁剪）：
1. 【任务目标】   固定，始终保留
2. 【历史摘要】   < budget * 20% 才加入
3. 【RAG 知识】   < budget * 30% 才加入（当前预留，intent=rag 时填充）
4. 【最近对话】   剩余 token 全给它（保留最近 8 轮 = 16 条消息）
```

---

## State 关键字段速查

```python
class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages]  # 自动追加
    intent: "react|chat|rag|unknown"
    context_str: str          # ContextBuilder 输出
    react_steps: list[ReActStep]  # 推理链（Trace 用）
    tool_calls: list[ToolCallRecord]
    current_step: int
    max_steps: int = 10
    critic_passed: bool | None   # None=未跑, True=通过, False=重试
    critic_feedback: str
    retry_count: int
    max_retries: int = 2
    final_answer: str
    token_usage: TokenUsage      # budget / used_prompt / used_completion
    error: str | None
    human_approved: bool | None
    session_id: str
```

---

## 图路由逻辑

```python
# Router 之后
intent in ("react", "rag") → context_builder
intent == "chat"           → finalize（跳过工具调用）

# Critic 之后
critic_passed == True                      → finalize
critic_passed == False, retry < max_retries → react_executor
critic_passed == False, retry >= max_retries → finalize（兜底）

# Human Approval（可选，use_human_approval=True 时启用）
human_approved == True  → memory_write
human_approved == False → END（丢弃）
```

---

## 模块依赖关系

```
agent_runtime.py
    └── graph.py（compile_graph）
            ├── nodes/router.py          → services/llm
            ├── nodes/context_builder.py → memory/manager.py → memory/short_term.py
            │                                               └── memory/summarizer.py
            ├── executors/react/executor.py → tools/registry.py
            │                             → executors/react/prompts.py
            │                             └── observability/trace.py
            ├── nodes/critic.py          → services/llm
            ├── nodes/finalize.py
            ├── nodes/memory_write.py    → memory/manager.py
            └── nodes/human_approval.py  (可选)
```

---

## 后续扩展接入点

| 扩展 | 接入位置 | 说明 |
|------|----------|------|
| RAG | `context_builder_node` | intent=rag 时调用 retriever，填充 state.rag_results |
| Multi-Agent | `graph.py` 新增子图节点 | 父 Agent 分解任务，子 Agent 作为节点执行 |
| MCP Tool | `tools/registry.py` | 新增 `register_mcp_tool()` 方法 |
| Planner | Router 和 ReAct 之间 | 新增 planner_node，输出 state.subtasks |
| Code Agent | `executors/code/` | 新增执行单元，支持沙箱运行代码 |
| Web Search | `tools/builtin/search.py` | 替换模拟实现，接入 Tavily/Serper API |
