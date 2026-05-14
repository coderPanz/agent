"""Agent-Trace: 结构化日志、Token 统计、推理链记录"""
from app.core.agent.observability.logger import get_logger, log_json


class Tracer:
    """
    结构化 Trace 记录器：记录节点流转、工具调用、Token 消耗、推理链。
    每个 session 一个实例。
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._logger = get_logger(f"trace.{session_id}")


    async def log_step_start(self, step: int):
        log_json(self._logger, "react_step_start", session=self.session_id, step=step)

    async def log_step_end(self, step: int, action: str, observation: str):
        log_json(self._logger, "react_step_end",
                 session=self.session_id, step=step,
                 action=action, obs_len=len(observation))

    async def log_final_answer(self, answer: str):
        log_json(self._logger, "final_answer",
                 session=self.session_id, answer_len=len(answer))

    async def log_error(self, step: int, error: str):
        log_json(self._logger, "error",
                 session=self.session_id, step=step, error=error)

    async def log_token_usage(self, prompt_tokens: int, completion_tokens: int):
        log_json(self._logger, "token_usage",
                 session=self.session_id,
                 prompt=prompt_tokens, completion=completion_tokens)

    async def log_node(self, node_name: str, status: str, **kwargs):
        log_json(self._logger, "node_transition",
                 session=self.session_id, node=node_name, status=status, **kwargs)

    