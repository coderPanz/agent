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


TypedDict 和 Pydantic 都是 Python 里用来 **给字典 / 数据做「类型校验」** 的工具，核心区别：
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
Annotated: 给类型添加额外的元数据（metadata）
基础语法：Annotated[真实类型, 元数据]
```python
from typing import Annotated
age: Annotated[int, "年龄必须大于18"]
```
- int → 真正的类型
- "年龄必须大于18" → 附加信息（metadata）
它只是：给框架、工具、IDE、类型检查器提供额外信息。
运行时会发生什么：  
```python
from typing import Annotated

x: Annotated[int, "hello"] = 1

print(type(x))
# 输出：<class 'int'>

```
LangGraph State 合并策略: Annotated[list, add]


## 2. 对话记忆：用 MessagesState 管理历史

LangGraph 预置了 `MessagesState`，帮你自动处理消息追加。
MessagesState = 官方预设好的 TypedDict

```python
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, AIMessage

# MessagesState 的 messages 字段是 Annotated[list, add_messages]，自动累加
graph = StateGraph(MessagesState)
# ...
```

MessagesState 的 messages 字段是 Annotated[list, add_messages]，自动累加
```python
from langgraph.graph import StateGraph, MessagesState, START, END

# 节点：接收消息，返回新消息
def chat_model(state: MessagesState):
    # 直接取对话历史
    last_message = state["messages"][-1]
    return {"messages": [f"AI 回复：{last_message}"]}

# 构建图：直接用 MessagesState
graph = StateGraph(MessagesState)
graph.add_node("chat", chat_model)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)

# 运行
app = graph.compile()
response = app.invoke({"messages": ["你好"]})
print(response["messages"])
# ['你好', 'AI 回复：你好']
```

使用 `MessagesState` 时，节点返回 `{"messages": [AIMessage("...")]}` 就会自动追加到历史，而不是覆盖。**强烈推荐直接用这个作为 MVP 的 State 基础。**
<!-- messagestate 结构 -->
```python
class MessagesState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```
messages 是消息对象列表，消息对象：SystemMessage、HumanMessage、AIMessage等
消息对象结构:  
msg.content      # 文本内容（最常用）
msg.type         # "human" / "ai" / "tool"
msg.name         # 角色名
msg.tool_calls   # AI 调用的工具（如果有）



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
  # state["messages"]
  # state = 当前图的状态
  # state["messages"] = 历史消息列表（用户说的 + AI 说的 + 工具返回的）
  # 格式：[HumanMessage, AIMessage, ToolMessage, ...]
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

# 从router 节点出发，执行router，记录状态 intent ，在执行 route_after_router 函数，根据 intent 决定下一步走向
# 如果 route_after_router 返回 "react"，则执行 react 节点，对应的fn
# 第三个参数： 把函数返回的字符串 → 映射成真正的节点名，函数返回 "react" → 跳去 "react" 节点，函数返回 END → 流程结束
builder.add_conditional_edges("router", route_after_router, {"react": "react", END: END})
# react 走完 - 直接结束
builder.add_edge("react", END)
graph = builder.compile()
```


**add_conditional_edges**： 它就是 LangGraph 里的「if /else 分支跳转， 流程图里的分支判断
```txt
builder.add_conditional_edges(
    从哪个节点出发,
    路由判断函数,
    映射字典（可选）
)

          ┌──→ weather →→ react 节点
router ───┤
          └──→ 其他   →→ END 结束
```

普通边（add_edge）：固定走哪条路： A → B
条件边（add_conditional_edges）：看情况走路： 
```txt
          ┌──→ weather →→ react 节点
router ───┤
          └──→ 其他   →→ END 结束
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
# interrupt 是 LangGraph 中用于中断图执行的核心工具，作用是让工作流在运行到指定节点时暂停，等待外部输入 / 操作后再继续执行，是实现人机交互、人工审核、外部决策的关键功能。
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


## 9. create_react_agent
create_react_agent 是 LangChain 提供的工厂函数，用来快速创建一个遵循 ReAct（Reasoning + Acting）模式的智能体（Agent）。它让大模型能用自然语言一步步思考、决定是否调用工具、并循环直到得出答案。
```python
def create_react_agent(
    model: BaseLanguageModel,
    tools: List[BaseTool],
    prompt: PromptTemplate,
    tools_renderer: Callable[[List[BaseTool]], str] = render_text_description,
    stop_sequence: Union[bool, List[str]] = True,
) -> Runnable
```

- model：大模型实例（如 ChatOpenAI、ChatAnthropic）
- tools：工具列表（用 @tool 装饰或继承 BaseTool）
- prompt：提示模板，必须包含 {tools}、{input}、{agent_scratchpad} 变量
- tools_renderer：工具渲染函数
- stop_sequence：是否自动添加停止符（默认 ["Observation:"]），防止模型继续生成幻觉内容

工作流程：
校验 Prompt：确保模板包含必需变量。
渲染工具描述：把工具列表转成自然语言文本，插入 Prompt 的 {tools} 位置。
设置停止序列：让模型在输出 Observation: 时暂停，等待工具返回结果。
组装执行链：返回一个 Runnable，可被 AgentExecutor 循环调用。

执行循环：用户输入 → LLM生成Thought/Action → 执行工具 → 返回Observation → 再次LLM → ... → Final Answer

```python
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# 1. 定义工具
@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

tools = [multiply]

# 2. 加载标准 ReAct Prompt（也可自定义）
prompt = hub.pull("hwchase17/react")

# 3. 初始化模型
model = ChatOpenAI(model="gpt-3.5-turbo")

# 4. 创建 Agent
agent = create_react_agent(model, tools, prompt)

# 5. 创建执行器并运行
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
result = agent_executor.invoke({"input": "What is 7 multiplied by 9?"})
print(result["output"])
```

输出：
```plaintext
> Entering new AgentExecutor chain...
Thought: I need to multiply 7 and 9.
Action: multiply
Action Input: {"a":7,"b":9}
Observation: 63
Thought: I now know the final answer
Final Answer: 63
> Finished chain.
63
```
