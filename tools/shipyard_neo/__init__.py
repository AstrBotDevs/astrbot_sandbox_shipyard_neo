from .browser import BrowserBatchExecTool, BrowserExecTool, RunBrowserSkillTool
from .neo_skills import (
    AnnotateExecutionTool,
    CreateSkillCandidateTool,
    CreateSkillPayloadTool,
    EvaluateSkillCandidateTool,
    GetExecutionHistoryTool,
    GetSkillPayloadTool,
    ListSkillCandidatesTool,
    ListSkillReleasesTool,
    PromoteSkillCandidateTool,
    RollbackSkillReleaseTool,
    SyncSkillReleaseTool,
)

SHIPYARD_NEO_TOOL_MODULE_PREFIX = __name__
SHIPYARD_NEO_TOOL_CLASSES = (
    BrowserExecTool,
    BrowserBatchExecTool,
    RunBrowserSkillTool,
    GetExecutionHistoryTool,
    AnnotateExecutionTool,
    CreateSkillPayloadTool,
    GetSkillPayloadTool,
    CreateSkillCandidateTool,
    ListSkillCandidatesTool,
    EvaluateSkillCandidateTool,
    PromoteSkillCandidateTool,
    ListSkillReleasesTool,
    RollbackSkillReleaseTool,
    SyncSkillReleaseTool,
)
SHIPYARD_NEO_TOOL_NAMES = frozenset(
    tool_cls.name for tool_cls in SHIPYARD_NEO_TOOL_CLASSES
)


def build_shipyard_neo_tools():
    return [tool_cls() for tool_cls in SHIPYARD_NEO_TOOL_CLASSES]


__all__ = [
    "AnnotateExecutionTool",
    "BrowserBatchExecTool",
    "BrowserExecTool",
    "CreateSkillCandidateTool",
    "CreateSkillPayloadTool",
    "EvaluateSkillCandidateTool",
    "GetExecutionHistoryTool",
    "GetSkillPayloadTool",
    "ListSkillCandidatesTool",
    "ListSkillReleasesTool",
    "PromoteSkillCandidateTool",
    "RollbackSkillReleaseTool",
    "RunBrowserSkillTool",
    "SyncSkillReleaseTool",
    "SHIPYARD_NEO_TOOL_CLASSES",
    "SHIPYARD_NEO_TOOL_MODULE_PREFIX",
    "SHIPYARD_NEO_TOOL_NAMES",
    "build_shipyard_neo_tools",
]
