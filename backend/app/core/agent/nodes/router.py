"""Agent-Router: 意图识别"""
import json
from langchain_core.message import SystemMessage, HumanMessage
from app.core.agent.state import AgentState, IntentType
from app.services.llm import init_llm_client

"""
langchain Message结构：  
message.content       # 字符串：消息正文（最重要）
message.type          # 字符串：消息类型（system/human/ai）
message.additional_kwargs  # 字典：额外参数（如 role、name）
"""


"""
类名	           .type值	         说明
HumanMessage	   "human"	        用户消息（user）
AIMessage	       "ai"	            AI 助手回复（assistant）
SystemMessage	   "system"	        系统提示词
ToolMessage	     "tool"	          工具返回结果
FunctionMessage	 "function"	      旧版 function call（legacy）
ChatMessage	     "chat"	          自定义 role 消息
"""

# 意图识别系统提示词
ROUTER_SYSTEM_PROMPT = """
你是一个意图分类器。根据用户最后一条消息，返回 JSON：
{"intent": "<react|chat|rag|unknown>"}

- react : 需要调用工具、查询数据、执行操作
- chat  : 普通聊天、闲聊、无需工具
- rag   : 需要在知识库中检索文档
- unknown: 无法判断

只输出 JSON，不要任何解释。
"""

async def router_node(state: AgentState) -> dict:
    """
    意图路由节点。
    读取最后一条用户消息 → 调用 LLM 分类 → 写回 intent 字段。
    """
    # 取最后一条用户消息内容
    last_user_msg = ""
    for msg in reversed(state.messages):
        if msg.type == "human":
            last_user_msg = msg.content
            break

    # 调用 LLM 分类
    llm = init_llm_client()
    resp = await llm.ainvoke([
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=last_user_msg),
    ])

    # 解析 JSON，容错处理
    try:
        result = json.loads(resp.content)
        intent: IntentType = result.get("intent", "unknown")
    except Exception:
        intent = "unknown"

    return {"intent": intent}





