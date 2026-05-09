**流程设计**
```mermaid
用户输入
  ↓
Router（判断意图）
  ↓
Context Builder（组装上下文：记忆 + 最近对话 + 检索 + 任务状态+提问用户补充）
  ↓
[主状态机开始循环， 维护节点状态流转，ctx传递、下一步走向，token分配、观察、异常处理等]
  ↓
  可选以下模式
    |_ ReAct（推理与行动）
        推理
        行动
        观察
        执行
        反思并修正【可选】
        return执行结果和必要上下文
    |_ Plan-and-Execute（先规划再执行）
        规划
        拆分任务
        执行任务
        反思并修正【可选】
        return执行结果和必要上下文
    |_ Multi-Agent（多Agent协作）
        分配任务
        sub-agent执行
        执行任务
        反思并修正【可选】
        return执行结果和必要上下文
    |_ AutoGPT（自主循环）
        自主循环
        反思并修正【可选】
        return执行结果和必要上下文
  ↓
Critic（可选，结果校验）
  ↓
Response
  ↓
Memory & Trace 写回
  ↓
[主状态机结束循环，汇总最终回复]
```

示例流程：
```yaml
用户请求
    │
    ▼
[意图路由] ─────── 选择图定义
    │
    ▼
[主状态机开始循环]
    │
    ├─→ [节点A: function] ── 更新ctx ──→ 路由决策
    ├─→ [节点B: react]  ──┐
    │   ├ 发送任务信封      │
    │   ├ Thought-Action循环 │
    │   ├ 工具调用+后处理    │
    │   └ 压缩历史输出结果 ──┘ 更新ctx ──→ 路由决策
    ├─→ [节点C: self_refine] ──┐
    │   ├ 生成初版              │
    │   ├ 反思并修正（最多3次）  │
    │   └ 输出最终版 ──────────┘ 更新ctx ──→ 路由决策
    │
    └─→ [END] ── 汇总最终回复
```

**工程设计**
- 节点定义标准化：用 YAML/JSON 描述每个节点，包含类型、输入schema、输出schema、工具列表、节点专用 prompt 模板。
- 上下文管道：所有节点输入都经过一个 ContextAssembler，它根据节点配置和当前 ctx 组装最终 prompt。
- 可观测性：在状态机转移、节点开始/结束、ReAct 每步、自我修正每轮处打点日志，并记录 Token 消耗。
- 异常处理：每个节点都可能抛出异常（工具超时、LLM格式错误），主状态机应定义 on_error 边，可跳转到降级节点或人工兜底。
- 需要有 human in the loop 机制


## 第一版
第一版只实现：
1. Router：最简单的意图分类（关键词或 LLM 单次调用）
2. Context Builder：拼装系统提示 + 最近 N 轮对话 + 必要的用户画像/知识（先不做复杂 RAG）
3. 主状态机：一个线性图（意图 → 执行节点 → 结束）
4. 执行单元：只实现 ReAct（带可选的自我修正开关）
5. Memory & Trace：会话级存储（Redis 或 dict），写回对话历史和关键结果









your_agent/
├── main.py           # 服务入口
├── graph.py           # 状态图定义
├── nodes/
│   ├── router.py      # 意图路由
│   ├── react_exec.py  # ReAct 执行节点
│   └── finalize.py    # 结束处理
├── context.py         # Context Builder
├── tools.py           # 工具定义
├── state.py           # 状态数据结构
└── memory.py          # 记忆读写




your_agent/
├── main.py                   # 服务入口，组装图并启动
├── graph.py                  # 主状态机定义（StateGraph）
├── state.py                  # AgentState 定义
├── context_builder.py        # Context Builder（上下文组装管道）
├── memory.py                 # 记忆管理（可选，MVP可简单存state）
│
├── nodes/                    # 所有状态机节点
│   ├── __init__.py
│   ├── router.py             # 意图路由节点
│   ├── finalize.py           # 结束处理节点
│   └── human_approval.py     # 人机协作节点（预留）
│
├── executors/                # 执行单元 (架构中的可插拔模式)
│   ├── __init__.py
│   ├── base.py               # 执行单元抽象基类
│   └── react/                # ReAct 执行单元
│       ├── __init__.py       # 暴露 create_react_executor 等
│       ├── executor.py       # ReAct 主逻辑（循环）
│       ├── prompts.py        # 提示词模板（系统指令、few-shot等）
│       ├── tools.py          # ReAct 专用的工具定义
│       ├── tool_processing.py # 工具输出后处理（裁剪、压缩等）
│       └── self_refine.py    # 可选的自我修正循环
│
├── tools/                    # 全局共享工具（可被多个执行单元使用）
│   ├── __init__.py
│   └── common_tools.py
│
├── llm/                      # LLM 实例化管理
│   └── client.py
│
├── config/                   # 配置
│   └── settings.py
│
└── utils/                    # 公共工具函数
    └── logger.py