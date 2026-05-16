# LangGraph 入门与状态图示例

这是一份面向 Python 和 LangGraph 新手的学习笔记。

学习目标：

1. 理解 LangGraph 是什么
2. 理解 State / Node / Edge 三个核心概念
3. 理解 `TypedDict`、`Annotated`、`MessagesState`
4. 能写出一个最小可运行的状态图
5. 能理解 Router、ReAct、Human-in-the-Loop、Checkpointer 的基本用法

---

## 1. LangGraph 是什么

LangGraph 是一个用来构建 **状态机 / 工作流图 / Agent 流程图** 的框架。

你可以把它理解成：

```text
数据 State
  ↓
节点 Node A
  ↓
节点 Node B
  ↓
结束 END
```

在 Agent 项目中，LangGraph 常用于控制这些流程：

- 用户输入
- 意图识别 Router
- 上下文构建 Context Builder
- ReAct 工具调用
- 人工审核 Human-in-the-Loop
- 最终回答

---

## 2. 安装

```bash
pip install langgraph langchain langchain-openai
```

如果项目使用 `uv`：

```bash
uv add langgraph langchain langchain-openai
```

---

## 3. 三个核心概念

| 概念 | 作用 | 新手理解 |
| --- | --- | --- |
| `State` | 节点之间传递的数据 | 整个流程的共享上下文 |
| `Node` | 处理 State 的函数 | 流程图里的一个步骤 |
| `Edge` | 节点之间的连接线 | 决定下一步去哪 |

例如：

```text
State = {"text": "start"}

node_a 处理后：{"text": "start→A"}
node_b 处理后：{"text": "start→A→B"}
```

---

## 4. TypedDict 与 Pydantic

LangGraph 的 State 通常用 `TypedDict` 或 Pydantic 模型定义。

### 4.1 TypedDict

`TypedDict` 用来描述字典结构。

```python
from typing import TypedDict


class State(TypedDict):
    text: str
```

含义：

```python
state = {
    "text": "hello"
}
```

`TypedDict` 的特点：

- 轻量
- 主要用于类型提示
- 运行时不会强制校验

### 4.2 Pydantic

Pydantic 会在运行时做数据校验。

```python
from pydantic import BaseModel


class State(BaseModel):
    text: str
```

区别：

| 工具 | 特点 |
| --- | --- |
| `TypedDict` | 轻量，适合 LangGraph State |
| Pydantic | 强校验，适合 API 请求 / 响应模型 |

新手建议：LangGraph 先用 `TypedDict`。

---

## 5. 最小 LangGraph 示例

这个例子演示固定流程：

```text
a → b → END
```

```python
# TypedDict 用来描述状态字典里有哪些字段，以及字段类型
from typing import TypedDict

# StateGraph 是 LangGraph 的状态图构建器；END 表示图执行结束
from langgraph.graph import StateGraph, END


# 定义整个图在节点之间传递的状态结构
class State(TypedDict):
    text: str


# 节点 A：接收当前 state，返回要更新的字段
def node_a(state: State):
    return {"text": state["text"] + "→A"}


# 节点 B：同样接收 state，并在 text 后面追加内容
def node_b(state: State):
    return {"text": state["text"] + "→B"}


# 创建一个状态图，告诉 LangGraph：这个图的状态类型是 State
builder = StateGraph(State)

# 注册节点名称和对应的执行函数
builder.add_node("a", node_a)
builder.add_node("b", node_b)

# 设置入口节点，图会从 a 开始执行
builder.set_entry_point("a")

# 设置固定流转路径：a 执行完进入 b
builder.add_edge("a", "b")

# b 执行完后进入 END，表示流程结束
builder.add_edge("b", END)

# 编译图，得到可运行的 graph 对象
graph = builder.compile()

# invoke 传入初始状态，LangGraph 会按边依次执行节点
result = graph.invoke({"text": "start"})

print(result)
# {'text': 'start→A→B'}
```

重点：

- 节点函数接收 `state`
- 节点函数返回一个字典
- 返回的字典会更新到 State 里
- `add_edge` 表示固定流程
- `END` 表示结束

---

## 6. State 更新规则

节点不需要返回完整 State，只需要返回要更新的字段。

```python
def node_a(state: State):
    return {"text": state["text"] + "→A"}
```

如果 State 里还有其他字段，没返回的字段会保留。

但是要注意：普通字段默认是覆盖更新。

例如：

```python
return {"text": "new"}
```

会把原来的 `text` 覆盖成 `"new"`。

---

## 7. Annotated 是什么

`Annotated` 可以给类型添加额外信息。

基础语法：

```python
from typing import Annotated

age: Annotated[int, "年龄必须大于18"]
```

拆开看：

- `int`：真正的类型
- `"年龄必须大于18"`：附加信息

运行时变量仍然是普通 `int`：

```python
from typing import Annotated

x: Annotated[int, "hello"] = 1

print(type(x))
# <class 'int'>
```

在 LangGraph 里，`Annotated` 常用于声明 State 的合并策略。

---

## 8. 列表字段如何追加而不是覆盖

如果 State 里有列表字段，默认返回新列表时可能会覆盖旧列表。

LangGraph 可以用 `Annotated` 指定合并方式。

例如消息列表常用 `add_messages`：

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
```

含义：

```text
旧 messages + 新 messages
```

而不是：

```text
新 messages 覆盖旧 messages
```

---

## 9. MessagesState

LangGraph 提供了内置的 `MessagesState`，专门用于聊天消息历史。

它大概等价于：

```python
class MessagesState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

也就是说：`messages` 会自动追加。

示例：

```python
from langgraph.graph import StateGraph, MessagesState, START, END


def chat_model(state: MessagesState):
    last_message = state["messages"][-1]
    return {"messages": [f"AI 回复：{last_message}"]}


builder = StateGraph(MessagesState)
builder.add_node("chat", chat_model)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

graph = builder.compile()

response = graph.invoke({"messages": ["你好"]})

print(response["messages"])
# ['你好', 'AI 回复：你好']
```

真实聊天项目里通常用消息对象：

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
```

常见消息对象：

| 类型 | 说明 |
| --- | --- |
| `SystemMessage` | 系统提示词 |
| `HumanMessage` | 用户消息 |
| `AIMessage` | AI 回复 |
| `ToolMessage` | 工具返回结果 |

消息常用字段：

```python
msg.content      # 文本内容
msg.type         # human / ai / system / tool
msg.name         # 名称，可选
msg.tool_calls   # AI 请求调用的工具，可选
```

---

## 10. 普通边 add_edge

普通边表示固定流转。

```python
builder.add_edge("a", "b")
```

意思是：

```text
a 执行完后，一定进入 b
```

适合固定流程：

```text
router → context_builder → react → final
```

---

## 11. 条件边 add_conditional_edges

条件边相当于流程图里的 `if / else`。

```python
builder.add_conditional_edges(
    "router",
    route_after_router,
    {
        "react": "react",
        "chat": "chat",
        END: END,
    },
)
```

含义：

```text
router 执行完
  ↓
调用 route_after_router(state)
  ↓
根据返回值决定下一个节点
```

示例：

```python
def route_after_router(state):
    if state["intent"] == "weather":
        return "react"
    return END
```

流程图：

```text
          ┌──→ react
router ───┤
          └──→ END
```

---

## 12. Router + ReAct 最小骨架

目标：

```text
用户输入
  ↓
Router 判断是否需要工具
  ↓
需要工具 → ReAct 节点
  ↓
结束
```

### 12.1 定义工具

```python
from langchain_core.tools import tool


@tool
def get_weather(city: str) -> str:
    """查询城市天气"""
    return f"{city}，25°C，晴"
```

### 12.2 定义 State

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str
```

### 12.3 Router 节点

```python
def router(state: AgentState):
    last_msg = state["messages"][-1].content

    if "天气" in last_msg:
        intent = "weather"
    else:
        intent = "general"

    return {"intent": intent}
```

### 12.4 ReAct 节点

```python
from langgraph.prebuilt import create_react_agent


react_agent = create_react_agent(llm, [get_weather])


def react_node(state: AgentState):
    result = react_agent.invoke({"messages": state["messages"]})
    return {"messages": result["messages"][-1:]}
```

说明：

- `create_react_agent` 会创建一个能调用工具的 Agent
- `state["messages"]` 是当前对话历史
- `result["messages"][-1:]` 表示只取最后一条回复，并保持列表格式

### 12.5 组装图

```python
from langgraph.graph import StateGraph, END


builder = StateGraph(AgentState)

builder.add_node("router", router)
builder.add_node("react", react_node)

builder.set_entry_point("router")


def route_after_router(state: AgentState):
    if state["intent"] == "weather":
        return "react"
    return END


builder.add_conditional_edges(
    "router",
    route_after_router,
    {
        "react": "react",
        END: END,
    },
)

builder.add_edge("react", END)

graph = builder.compile()
```

### 12.6 运行

```python
from langchain_core.messages import HumanMessage


config = {"configurable": {"thread_id": "demo-1"}}

result = graph.invoke(
    {"messages": [HumanMessage(content="北京天气如何？")]},
    config,
)

print(result["messages"][-1].content)
```

---

## 13. ReAct 是什么

ReAct = Reasoning + Acting。

简单理解：

```text
Thought：我需要查询天气
Action：调用 get_weather
Action Input：{"city": "北京"}
Observation：北京，25°C，晴
Thought：我已经拿到结果
Final Answer：北京今天 25°C，晴
```

它适合：

- 需要调用工具
- 需要多步推理
- 需要根据工具返回继续判断

---

## 14. create_react_agent

`create_react_agent` 是 LangGraph 提供的快速创建 ReAct Agent 的方法。

常见用法：

```python
from langgraph.prebuilt import create_react_agent


react_agent = create_react_agent(llm, tools)
```

参数：

| 参数 | 说明 |
| --- | --- |
| `llm` | 大模型实例 |
| `tools` | 工具列表 |

执行流程：

```text
用户输入
  ↓
LLM 判断是否需要工具
  ↓
生成工具调用
  ↓
执行工具
  ↓
把工具结果作为 Observation
  ↓
LLM 继续生成最终回答
```

---

## 15. 自我修正 Self-Refine

自我修正常放在 ReAct 节点内部，不一定要新增图节点。

示例：

```python
def react_with_self_refine(state: AgentState):
    result = react_agent.invoke({"messages": state["messages"]})
    final_answer = result["messages"][-1].content

    for _ in range(2):
        critique_prompt = f"请检查以下回复是否准确完整。如果没有问题，只回答 OK：{final_answer}"
        critique = llm.invoke([HumanMessage(content=critique_prompt)]).content

        if "OK" in critique:
            break

        refine_prompt = f"根据批评意见修改回答。\n批评：{critique}\n原回答：{final_answer}"
        final_answer = llm.invoke([HumanMessage(content=refine_prompt)]).content

    return {"messages": [AIMessage(content=final_answer)]}
```

注意：

- 必须设置最大轮数
- 否则可能无限反思
- 第一版建议最多 1-2 轮

---

## 16. Human-in-the-Loop

Human-in-the-Loop 表示人工介入。

适合：

- 发送邮件前确认
- 删除数据前确认
- 执行高风险操作前确认

LangGraph 使用 `interrupt` 暂停图执行。

```python
from langgraph.types import interrupt


def human_approval(state: AgentState):
    draft = state["messages"][-1].content

    decision = interrupt({
        "question": "是否批准此回复？",
        "draft": draft,
    })

    return {"approved": decision.get("approved", False)}
```

图中接入：

```python
builder.add_node("human_approval", human_approval)
builder.add_edge("react", "human_approval")
```

恢复执行：

```python
from langgraph.types import Command


config = {"configurable": {"thread_id": "user-123"}}

for event in graph.stream(
    Command(resume={"approved": True}),
    config,
    stream_mode="values",
):
    print(event)
```

关键点：使用 `interrupt` 时，必须使用 checkpointer 保存状态。

---

## 17. Checkpointer

Checkpointer 用来保存图执行过程中的状态。

开发环境可以使用内存版本：

```python
from langgraph.checkpoint.memory import MemorySaver


memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
```

生产环境可换成：

- SQLite
- Postgres
- Redis

使用 checkpointer 后，每次调用都建议带上 `thread_id`：

```python
config = {
    "configurable": {
        "thread_id": "session-001",
    }
}
```

`thread_id` 的作用是区分不同用户或不同会话。

---

## 18. 上下文窗口治理

Agent 对话越长，消息越多，模型输入就越长。

最简单做法：只保留最近 N 条消息。

```python
def react_node(state: AgentState):
    recent = state["messages"][-20:]
    result = react_agent.invoke({"messages": recent})
    return {"messages": result["messages"][-1:]}
```

工具输出也要截断：

```python
@tool
def search(query: str):
    raw = "很长很长的搜索结果"
    return raw[:2000]
```

原因：

- 防止上下文窗口爆炸
- 降低 token 成本
- 避免无关历史影响回答

---

## 19. 完整 MVP 示例

```python
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent


@tool
def get_weather(city: str) -> str:
    """查询城市天气"""
    return f"{city}：晴，25°C"


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
react_agent = create_react_agent(llm, [get_weather])


def router(state: AgentState):
    text = state["messages"][-1].content
    intent = "weather" if "天气" in text else "chat"
    return {"intent": intent}


def react_node(state: AgentState):
    recent = state["messages"][-20:]
    result = react_agent.invoke({"messages": recent})
    return {"messages": result["messages"][-1:]}


builder = StateGraph(AgentState)
builder.add_node("router", router)
builder.add_node("react", react_node)

builder.set_entry_point("router")


def route_after_router(state: AgentState):
    if state["intent"] == "weather":
        return "react"
    return END


builder.add_conditional_edges(
    "router",
    route_after_router,
    {
        "react": "react",
        END: END,
    },
)

builder.add_edge("react", END)

graph = builder.compile()

result = graph.invoke({
    "messages": [HumanMessage(content="上海天气怎么样？")]
})

print(result["messages"][-1].content)
```

---

## 20. 学习路线建议

建议按这个顺序学习：

1. 先理解 `StateGraph`
2. 再理解 `State`
3. 再写普通边 `add_edge`
4. 再写条件边 `add_conditional_edges`
5. 再学习 `MessagesState`
6. 再接入 `create_react_agent`
7. 最后学习 `interrupt` 和 checkpointer

不要一开始就学完整 Agent。先把这个流程跑通：

```text
输入 → router → react → END
```

再逐步加入：

- 记忆
- 工具
- 自我修正
- 人工审批
- 持久化

---

## 21. 常见问题

### 21.1 为什么节点只返回部分字段

因为 LangGraph 会把节点返回的字段合并进 State。

```python
return {"intent": "weather"}
```

只更新 `intent`，其他字段保留。

### 21.2 为什么 messages 要用 Annotated

因为消息历史通常需要追加，而不是覆盖。

```python
messages: Annotated[list, add_messages]
```

表示新消息会追加到旧消息后面。

### 21.3 END 是什么

`END` 是 LangGraph 的结束标记。

```python
builder.add_edge("react", END)
```

表示 `react` 节点执行完后，整个图结束。

### 21.4 graph.invoke 做了什么

`graph.invoke(initial_state)` 会：

1. 接收初始 State
2. 从入口节点开始执行
3. 按边流转
4. 每个节点更新 State
5. 返回最终 State

### 21.5 stream 和 invoke 有什么区别

- `invoke`：一次性执行完，返回最终结果
- `stream`：边执行边返回中间状态

流式接口适合：

- SSE
- WebSocket
- 前端展示执行进度
