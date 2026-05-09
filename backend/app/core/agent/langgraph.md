---

## 1. 安装与核心概念（5 分钟）

### 安装

```bash
pip install langgraph langchain langchain-openai
```

### 三大核心概念


| 概念        | 作用                                      |
| --------- | --------------------------------------- |
| **State** | 流过所有节点的数据容器，是一个 TypedDict / Pydantic 模型 |
| **Node**  | Python 函数，接收当前 State，返回部分 State 更新      |
| **Edge**  | 连接节点的线；普通边 `a → b`，条件边 `a → 分支`         |


TypedDict 和 Pydantic 都是 Python 里用来 ** 给字典 / 数据做「类型校验」** 的工具，核心区别：
TypedDict：轻量、仅静态类型检查（写代码时提示，运行时不报错）
Pydantic：功能强大、运行时强制校验（真正拦截错误数据）

### 一个图的最小结构

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
builder.add_edge("a", "b")          # 固定边
# b 执行完后进入 END，表示流程结束
builder.add_edge("b", END)          # 结束
# 编译图，得到可运行的 graph 对象
graph = builder.compile()

# invoke 传入初始状态，LangGraph 会按边依次执行节点
result = graph.invoke({"text": "start"})
print(result)  # {'text': 'start→A→B'}
```

**重点**：

- 节点函数**只返回需要更新的字段**，其余字段保持不变。
- State 默认是**浅合并**；如果字段是列表，推荐用 `Annotated[list, operator.add]` 实现追加而非覆盖（后面会演示）。

---

## 2. 对话记忆：用 MessagesState 管理历史

LangGraph 预置了 `MessagesState`，帮你自动处理消息追加。

```python
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, AIMessage

# MessagesState 的 messages 字段是 Annotated[list, add_messages]，自动累加
graph = StateGraph(MessagesState)
# ...
```

使用 `MessagesState` 时，节点返回 `{"messages": [AIMessage("...")]}` 就会自动追加到历史，而不是覆盖。**强烈推荐直接用这个作为 MVP 的 State 基础。**

---

## 3. 构建你的第一个“意图路由 + ReAct”图（核心骨架）

目标：用户输入 → Router 分类 → ReAct 节点（调用工具） → 结束。

### 3.1 定义工具

```python
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """查询城市天气"""
    return f"{city}，25°C，晴"
```

### 3.2 创建 Router 节点

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(model="gpt-4o-mini")

def router(state: MessagesState):
    last_msg = state["messages"][-1].content
    # 简单意图识别（实际可用结构化输出）
    if "天气" in last_msg:
        intent = "weather"
    else:
        intent = "general"
    return {"intent": intent}   # 你需要在 State 中加入 intent 字段
```

### 3.3 创建 ReAct 节点（最快方式：用预构建的 create_react_agent）

```python
from langgraph.prebuilt import create_react_agent

react_agent = create_react_agent(llm, [get_weather])

# 然后直接在图中作为一个节点调用
def react_node(state: MessagesState):
    result = react_agent.invoke({"messages": state["messages"]})
    # 只把最后一条回复作为最终答案传回
    return {"messages": result["messages"][-1:]}
```

### 3.4 组合图（带条件边）

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str

builder = StateGraph(AgentState)
builder.add_node("router", router)
builder.add_node("react", react_node)

builder.set_entry_point("router")

def route_after_router(state: AgentState):
    if state["intent"] == "weather":
        return "react"
    else:
        return END       # 无工具需求直接结束

builder.add_conditional_edges("router", route_after_router, {"react": "react", END: END})
builder.add_edge("react", END)
graph = builder.compile()
```

运行：

```python
config = {"configurable": {"thread_id": "1"}}
res = graph.invoke({"messages": [HumanMessage(content="北京天气如何？")]}, config)
print(res["messages"][-1].content)
```

**这就是 MVP 的全部骨架，足够覆盖 80% 的场景。**

---

## 4. 加入自我修正（在 ReAct 节点内）

在 `react_node` 内部增加一个反思循环（不破坏图结构）：

```python
def react_with_self_refine(state: MessagesState):
    # 第一次生成
    result = react_agent.invoke({"messages": state["messages"]})
    final_answer = result["messages"][-1].content

    # 自我修正最多 2 轮
    for i in range(2):
        critique_prompt = f"请审查以下回复是否准确、完整，如果是则回复'OK'，否则指出问题：{final_answer}"
        critique = llm.invoke([HumanMessage(content=critique_prompt)]).content

        if "OK" in critique:
            break

        refine_prompt = f"根据批评修改：{critique}\n原回复：{final_answer}"
        final_answer = llm.invoke([HumanMessage(content=refine_prompt)]).content

    return {"messages": [AIMessage(content=final_answer)]}
```

然后图中使用 `react_with_self_refine` 替换原来的 `react_node`，开关可通过 state 的一个字段控制。

---

## 5. 人工干预（Human-in-the-Loop）三步接入

### 5.1 在需要审批的节点中调用 `interrupt`

```python
from langgraph.types import interrupt

def human_approval(state: AgentState):
    draft = state["messages"][-1].content
    # 暂停，等待外部传入用户决策
    user_decision = interrupt({
        "question": "是否发送？",
        "draft": draft
    })
    if user_decision.get("approved"):
        return {"approved": True}
    else:
        return {"approved": False}
```

### 5.2 图接入这个节点

在 `react_node` 和 `END` 之间插入 `human_approval`：

```python
builder.add_node("human_approval", human_approval)
builder.add_edge("react", "human_approval")
builder.add_conditional_edges(
    "human_approval",
    lambda s: "send" if s["approved"] else END,
    {"send": "send_email_node", END: END}
)
```

### 5.3 恢复执行

图形暂停后，你的后端接口这样做：

```python
from langgraph.types import Command

# 用户点击“批准”后调用
resume_config = {"configurable": {"thread_id": "user-123"}}
for event in graph.stream(Command(resume={"approved": True}), resume_config, stream_mode="values"):
    pass  # 或实时推送状态
```

**关键点**：`interrupt` 会自动保存状态到 checkpointer，所以你**必须使用 checkpointer**。

---

## 6. 持久化：加 checkpointer

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()          # 开发用
graph = builder.compile(checkpointer=memory)
```

生产环境换 `SqliteSaver` 或 `PostgresSaver`。

有了 checkpointer，每次调用都需要 `config` 中的 `thread_id` 来区分会话。

---

## 7. 上下文窗口治理（简单但必要）

在 ReAct 节点中，如果消息太多，截取最近 N 条：

```python
def react_node(state: MessagesState):
    recent = state["messages"][-20:]   # 保留最近20条
    result = react_agent.invoke({"messages": recent})
    return {"messages": result["messages"][-1:]}
```

工具输出截断可以在工具定义中做：

```python
@tool
def search(query: str):
    raw = ...   # 可能很长
    return raw[:2000]      # 强制截断
```

---

## 8. 完整的 MVP 代码模板（开箱即用）

```python
import os
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

# ------- 工具 -------
@tool
def get_weather(city: str) -> str:
    """获取指定城市天气"""
    return f"{city}：晴，25°C"

# ------- 状态 -------
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str
    approved: bool

# ------- LLM -------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ------- 节点 -------
def router(state: AgentState):
    text = state["messages"][-1].content
    intent = "weather" if "天气" in text else "chat"
    return {"intent": intent}

# React 执行（带窗口限制）
react_agent = create_react_agent(llm, [get_weather])

def react_node(state: AgentState):
    recent = state["messages"][-20:]   # 防止窗口爆炸
    result = react_agent.invoke({"messages": recent})
    last = result["messages"][-1]
    return {"messages": [last], "approved": False}

def human_approval(state: AgentState):
    draft = state["messages"][-1].content
    decision = interrupt({
        "draft": draft,
        "question": "是否批准此回复？（approved: True/False）"
    })
    return {"approved": decision.get("approved", False)}

def send_response(state: AgentState):
    # 这里可执行真实动作，此处仅标记
    return {"messages": [AIMessage(content="✅ 已发送最终回复")] }

# ------- 图 -------
builder = StateGraph(AgentState)
builder.add_node("router", router)
builder.add_node("react", react_node)
builder.add_node("human_approval", human_approval)
builder.add_node("send", send_response)

builder.set_entry_point("router")

def route_after_router(state: AgentState) -> Literal["react", "__end__"]:
    return "react" if state["intent"] == "weather" else END

builder.add_conditional_edges("router", route_after_router)
builder.add_edge("react", "human_approval")

def after_approval(state: AgentState) -> Literal["send", "__end__"]:
    return "send" if state["approved"] else END

builder.add_conditional_edges("human_approval", after_approval)
builder.add_edge("send", END)

graph = builder.compile(checkpointer=MemorySaver())

# ------- 使用演示 -------
config = {"configurable": {"thread_id": "demo-1"}}
# 第一次调用，会停在 human_approval
try:
    graph.invoke({"messages": [HumanMessage(content="上海天气怎么样？")]}, config)
except Exception:
    pass  # 实际会产生 GraphInterrupt，这里为演示简化

# 模拟用户决策：批准
for event in graph.stream(Command(resume={"approved": True}), config, stream_mode="values"):
    print(event)
```

---

