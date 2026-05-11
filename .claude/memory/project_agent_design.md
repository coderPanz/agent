---
name: Agent 技术方案核心架构决策
description: 第二版 Agent 系统的关键架构设计决策，避免每次重新解释
type: project
originSessionId: f7f05be4-dddf-4c65-91a4-0fe439b4f10f
---
> 详细架构图和完整执行流程见 `project_agent_architecture.md`，本文件只记录关键**决策原因**。

## 核心架构：图式状态机 + ReAct 执行单元

**设计选择：** LangGraph StateGraph 作为主状态机，ReAct 执行器**手动实现**（不用 `create_react_agent`）

**Why:** `create_react_agent` 无法精确控制每步 Prompt、无法记录推理链到 State、无法做 hallucination 防护
**How to apply:** 实现 ReAct 时，始终走 `executors/react/executor.py` 的手动循环方案

---

## State 设计决策

- 使用 **Pydantic BaseModel**（不用 TypedDict），原因：运行时类型校验更严格
- `messages` 字段用 `Annotated[list[BaseMessage], add_messages]`，自动追加不覆盖
- `critic_passed` 用**三值逻辑**：`None`（未跑）/ `True`（通过）/ `False`（需重试）
- `token_usage` 嵌套 TokenUsage 模型，全局 token 预算管控

---

## 节点流转

```
START → router → context_builder → react_executor → critic
    ↓ (chat)                                         ↓ (pass)
  finalize ←──────────────────────────────────── finalize
                                                     ↓ (fail, retry_count < max)
                                              react_executor (重试)
finalize → memory_write → END
```

---

## 工具系统

- **ToolRegistry 单例**：`ToolRegistry.get_instance()`
- 注册方式：装饰器 `@registry.register(name, description, timeout, max_retry)`
- 内置超时（`asyncio.wait_for`）+ 重试
- 工具输出截断为 2000 字符，防止 token 爆炸
- hallucination 防护：在 ReAct 循环中检查 `registry.has_tool(action_name)`，不存在则返回错误 Observation

---

## Memory 三层模型

- **短期**：in-memory dict，会话内有效（`memory/short_term.py`）
- **长期**：预留（目前未实现，接口在 `memory/manager.py`）
- **摘要**：超过 20 条消息自动压缩（`memory/summarizer.py`）

---

## Critic 节点

- Critic 位于 react_executor 之后
- `retry_count >= max_retries` 时强制通过（兜底），防止无限循环
- Critic 失败时写入 `critic_feedback`，下一轮 ReAct 可以读取用于改进

---

## 全局约定

- 所有节点函数签名：`async def xxx_node(state: AgentState) -> dict:`
- 节点只返回需要修改的字段的 dict，不返回完整 state
- 所有 LLM 调用用 `ainvoke`（异步），配合整个图的 async 风格
- LLM 初始化通过 `app.services.llm.init_llm_client()` 统一获取
