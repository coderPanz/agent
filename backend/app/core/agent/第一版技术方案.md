你是一名资深 AI Agent 架构师与 Python 工程师。
请基于我当前的第一版 Agent 架构设计，重新设计并实现一个「可扩展、工程化、可维护」的 Agent 系统。
第一版：图式状态机主控 + ReAct 子节点 + 必要时自我修正
---
# 当前目录结构（第一版）
```txt
backend/app/core/agent/
  ├── agent.py
  ├── context.py
  ├── graph.py
  ├── memory.py
  ├── router.py
  ├── state.py
  ├── tools.py
  ├── trace.py
  ├── executors/
  │   ├── base.py
  │   └── react/
  │       ├── context.py
  │       ├── executor.py
  │       ├── memory.py
  │       ├── prompts.py
  │       ├── router.py
  │       ├── self_refine.py
  │       ├── tool_processing.py
  │       └── tools.py

⸻

Agent 流程设计

flowchart TD
A[用户输入] --> B[Router 意图判断]
B --> C[Context Builder\n组装上下文]
C --> D[主状态机循环]
D --> E{选择执行模式}
E --> F[ReAct Agent]
F --> F1[推理 Thought]
F1 --> F2[行动 Action]
F2 --> F3[观察 Observation]
F3 --> F4[执行 Execution]
F4 --> F5[反思修正 Self Refine 可选]
F5 --> F6[返回结果与上下文]
F6 --> G[Critic 结果校验 可选]
G --> H[Response 最终回复]
H --> I[Memory & Trace 写回]
I --> J[状态机结束]

⸻

技术要求
使用以下技术栈实现：
* LangGraph
* LangChain
* Python
* Pydantic
* Async / Await
* 可插拔 Tool 机制
* 支持流式输出（Streaming）
* 支持 Memory
* 支持 Trace / 日志
* 支持 Human-in-the-loop
* 支持 Context Engineering
* 支持 Self-Refine
* 支持 Future RAG 接入
* 支持 Token Budget 管理
* 支持异常恢复与重试
* 支持节点级状态流转
⸻

核心目标

请不要只给概念设计，而是：
1. 重新设计完整工程架构
2. 设计模块职责
3. 设计状态流转
4. 设计 Context 管理机制
5. 设计 Router 机制
6. 设计 ReAct Executor
7. 设计 Critic 节点
8. 设计 Memory 模块
9. 设计 Trace / 可观测性
10. 设计 Tool 调度系统
11. 设计 Graph 编排
12. 给出完整代码实现
13. 所有代码必须带详细中文注释
14. 代码必须符合真实工程项目结构
15. 使用 async 风格实现
16. 需要体现“工程化 Agent”设计思想
17. 要考虑后续扩展多 Agent / Workflow / RAG

⸻

重点要求

请重点体现以下能力：

1. 主状态机（非常重要）

需要实现：

* 节点状态流转
* ctx 传递
* 下一步路由
* 中断恢复
* human in the loop
* token 分配
* retry
* timeout
* error fallback
* 观察机制
* 生命周期管理

不要只写简单 graph。

而是实现一个真正的：

* Agent Runtime
* Agent Orchestrator
* Agent State Machine

⸻

2. Context Engineering（重点）

需要实现：

Context Builder

负责：

* 最近对话
* Memory
* Summary
* RAG（预留）
* Tool Result
* Task 状态
* 用户补充信息
* 当前执行目标
* Token Budget

上下文需要支持：

* 裁剪
* 优先级
* 动态拼接
* 压缩
* 滑动窗口
* summarize

⸻

3. ReAct Executor（重点）

不要只调用 create_react_agent。

需要自行实现：

* Thought
* Action
* Observation
* Tool Call
* Tool Result
* Self Refine

并实现：

* 最大步骤限制
* 工具失败恢复
* hallucination 防护
* 工具结果验证
* structured output

⸻

4. Tool 系统

实现：

* Tool Registry
* Tool Executor
* Tool 权限控制
* Tool 超时
* Tool Retry
* Tool Schema 校验
* Tool Result 标准化

支持：

* LangChain Tool
* MCP Tool（预留）
* 自定义 Tool

⸻

5. Memory 系统

实现：

* 短期记忆
* 长期记忆
* Summary Memory
* Session Memory
* Memory 写回策略

⸻

6. Trace / Observability

实现：

* 节点日志
* Tool 调用日志
* Token 消耗日志
* 推理链日志
* Error Trace
* State Snapshot

最好给出：

* trace.py
* logger.py
* callback_handler.py

⸻

输出要求

请严格按以下顺序输出：

1. 总体架构设计

* 模块职责
* 调用链
* 生命周期

2. 推荐目录结构

* 工程级目录树
* 每个模块作用

3. Agent State 设计

* Pydantic State
* ctx 结构

4. Graph 设计

* LangGraph 状态流转
* 条件路由

5. Router 实现

6. Context Builder 实现

7. ReAct Executor 实现

8. Tool 系统实现

9. Memory 实现

10. Critic 实现

11. Trace / Logging 实现

12. Agent Runtime 实现

13. 完整运行示例

14. 后续如何扩展：

* Multi Agent
* Planner
* Workflow
* RAG
* MCP
* Web Search
* Code Agent

⸻

代码要求

代码必须：
* 可运行
* 不要伪代码
* 不要省略关键逻辑
* 必须有中文注释
* 使用 Python typing
* 使用 async
* 使用 Pydantic
* 使用 LangGraph 最佳实践
* 避免过度 toy demo 化

⸻

风格要求
* 工程化
* 模块化
* 高内聚低耦合
* 易扩展
* 清晰
* 偏真实生产级实现

给出渐进式的设计实现方案，一步一个脚印，我是python新手，慢慢来，生成实现的技术方案+代码架构实现+代码示例（清晰易懂的中文注释）的 md 文档，具体代码我来实现就好。