"""
Agent-ReAct-Executor: Thought→Action→Observation 循环
不使用 create_react_agent，而是手动实现 Thought → Action → Observation 循环，原因：
- 可以精确控制每一步的 Prompt
- 可以自定义工具失败恢复
- 可以在循环中记录每一步到 react_steps（用于 Trace）
- 可以做 hallucination 防护（检测模型是否捏造了不存在的工具）
"""

import json
import re # py 正则表达式模块d
import time
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.agent.state import AgentState, ReActStep, ToolCallRecord
from app.core.agent.tools.registry import ToolRegistry
from app.core.agent.executors.react.prompts import REACT_SYSTEM_PROMPT, OBSERVATION_TEMPLATE
from app.core.agent.observability.trace import Tracer
from app.services.llm import init_llm_client

# 从 LLM 输出中解析 Action 和 Action Input
# re.compile：将正则表达式提前编译好，后续方便使用
# 提取 Action 后的内容
ACTION_RE = re.compile(r"Action:\s*(.+)")
# 提取 Input 后的内容
ACTION_INPUT_RE = re.compile(r"Action Input:\s*(\{.+?\})", re.DOTALL)
# 提取 Final Answer 后内容
FINAL_ANSWER_RE = re.compile(r"Final Answer:\s*(.+)", re.DOTALL)
# 提取 Thought 里的内容
THOUGHT_RE = re.compile(r"Thought:\s*(.+?)(?=\nAction|\nFinal Answer|$)", re.DOTALL)


def _parse_llm_output(text: str) -> dict:
    """
      解析 LLM 的 ReAct 格式输出。
      返回: {"thought": ..., "action": ..., "action_input": ..., "final_answer": ...}
      其中 action/action_input 或 final_answer 必有其一。
    """
    # 用字典保存从 LLM 输出中解析出来的各个字段
    result = {}

    """
      thought_match.group(0)  # 整段匹配到的文本
      thought_match.group(1)  # 第 1 个括号捕获到的内容
      thought_match.start()   # 匹配开始位置
      thought_match.end()     # 匹配结束位置
    """
    thought_match = THOUGHT_RE.search(text)
    result["thought"] = thought_match.group(1).strip() if thought_match else ""

    final_match = FINAL_ANSWER_RE.search(text)
    if final_match:
        result["final_answer"] = final_match.group(1).strip()

    action_match = ACTION_RE.search(text)
    result["action_match"] = action_match.group(1).strip() if action_match else ""

    input_match = ACTION_INPUT_RE.search(text)
    if action_match:
        result["action"] = action_match.group(1).strip()
        try:
            result["action_input"] = json.loads(input_match.group(1)) if input_match else {}
        except json.JSONDecodeError:
            result["action_input"] = {}

    return result

async def react_executor_node(state: AgentState) -> dict:
    """ ReAct 执行节点 """

    # 1. 初始化 llm-tool-trace
    llm_client = init_llm_client()
    registry = ToolRegistry.get_instance()
    tracer = Tracer(session_id=state.session_id)

    # 2. though

    # ── 构建工具描述文本，注入 Prompt ──────────────────────
    tool_desc = registry.get_descriptions()
    system_prompt = REACT_SYSTEM_PROMPT.format(
        tool_descriptions=tool_desc,
        max_steps=state.max_steps,
    )

    # ── 初始化对话历史（包含 ContextBuilder 组装的上下文） ──
    history = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=f"上下文信息：\n{state.context_str}"),
        *state.messages,
    ]

    # ── ReAct 主循环 ───────────────────────────────────────
    react_steps: list[ReActStep] = []
    tool_calls: list[ToolCallRecord] = []
    current_step = state.current_step

    for step in range(current_step, state.max_steps):
        # 1. 记录开始
        await tracer.log_step_start(step)
        
        # 解析输出过程
        llm_response = await llm_client.ainvoke(history)
        raw_text = llm_response.content
        parsed = _parse_llm_output(raw_text)
        thought = parsed.get("thought", "")

        # 2. 如果是 Final Answer，退出循环
        if "final_answer" in parsed:
            react_steps.append(ReActStep(
                step=step,
                thought=thought,
                action=None,
                observation="[最终回答]",
            ))
            # 把最终回答追加到消息历史
            history.append(AIMessage(content=raw_text))
            await tracer.log_final_answer(parsed["final_answer"])
            return {
                "final_answer": parsed["final_answer"],
                "react_steps": react_steps,
                "tool_calls": tool_calls,
                "current_step": step + 1,
                "messages": [AIMessage(content=parsed["final_answer"])],
            }
        
        # 没有 action 时的情况处理-防止死循环
        if "action" not in parsed:
            await tracer.log_error(step, "LLM 输出既无 Action 也无 Final Answer")
            break
        
        action_name = parsed["action"]
        action_input = parsed.get("action_input", {})
        
        # 3. 验证工具名（防止 hallucination：模型捏造不存在的工具）
        if not registry.has_tool(action_name):
            observation = f"错误：工具 '{action_name}' 不存在，可用工具：{registry.list_tool_names()}"
            await tracer.log_error(step, observation)
            break
        
        else:
            # 工具调用
            # time.monotonic() = 不会往回跳的计时器-只保证：时间永远递增，不会因为系统时间修改而变小
            t0 = time.monotonic()
            tool_result = await registry.execute(action_name, action_input)
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            observation = tool_result.output
            tool_calls.append(ToolCallRecord(
                tool_name=action_name,
                input=action_input,
                output=observation,
                success=tool_result.success,
                elapsed_ms=elapsed_ms,
                error=tool_result.error,
            ))

        # 记录 ReActStep
        react_steps.append(ReActStep(
            step=step,
            thought=thought,
            action=action_name,
            observation=observation,
        ))

        # 把 Observation 追加到 history，进入下一步
        obs_text = OBSERVATION_TEMPLATE.format(result=observation)
        history.append(AIMessage(content=raw_text))
        history.append(HumanMessage(content=obs_text))
        await tracer.log_step_end(step, action_name, observation)


    # 超出 max_steps 时兜底回复
    fallback = "已达到最大推理步数，无法得出明确答案，请换一种方式提问。"
    return {
        "final_answer": fallback,
        "react_steps": react_steps,
        "tool_calls": tool_calls,
        "current_step": state.max_steps,
        "messages": [AIMessage(content=fallback)],
    }

    # 4. observation 过程




