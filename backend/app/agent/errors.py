"""Agent 基础层内部错误；对外只返回固定安全文案。"""


class ToolHandlerError(RuntimeError):
    """已知业务工具失败，不携带底层异常或秘密。"""


class AgentContextError(ValueError):
    """观察上下文无法安全构造。"""
