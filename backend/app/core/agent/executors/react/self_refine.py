from langchain_core.messages import HumanMessage
from app.services.llm import init_llm_client

REFINE_PROMPT = """
请审查以下回答是否准确、完整、逻辑清晰。

原始问题：{question}
当前回答：{answer}

如果回答已经足够好，请回复：PASS
如果有问题，请指出问题，然后给出改进后的完整回答，格式：
REVISE: <改进后的回答>
"""

async def self_refine(question: str, answer: str, max_rounds: int = 2) -> str:
    """
    自我修正：让 LLM 审查自己的输出，最多修正 max_rounds 次。
    返回最终（可能已修正的）回答。
    """
    llm = init_llm_client()
    current_answer = answer

    #_：这是一个惯用占位符，表示循环变量不需要使用。
    for _ in range(max_rounds):
        prompt = REFINE_PROMPT.format(question=question, answer=current_answer)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        text = resp.content.strip()

        # 用于判断一个字符串 是否以指定的前缀开头
        if text.startswith("PASS"):
            break   # 通过，不需要修改
        elif text.startswith("REVISE:"):
            current_answer = text[len("REVISE:"):].strip()
        else:
           break   # 格式异常，保留原答案
    return current_answer


