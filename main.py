from astrbot.api.star import Context, Star, register
from astrbot.core.computer.computer_client import (
    register_sandbox_provider,
    unregister_sandbox_provider,
)
from astrbot.core.provider.register import llm_tools

from .provider import ShipyardNeoSandboxProvider
from .tools.shipyard_neo import (
    AnnotateExecutionTool,
    BrowserBatchExecTool,
    BrowserExecTool,
    CreateSkillCandidateTool,
    CreateSkillPayloadTool,
    EvaluateSkillCandidateTool,
    GetExecutionHistoryTool,
    GetSkillPayloadTool,
    ListSkillCandidatesTool,
    ListSkillReleasesTool,
    PromoteSkillCandidateTool,
    RollbackSkillReleaseTool,
    RunBrowserSkillTool,
    SyncSkillReleaseTool,
)


@register(
    "astrbot-sandbox-shipyard-neo",
    "AstrBot Team",
    "Shipyard Neo sandbox runtime provider for AstrBot",
    "0.1.0",
)
class ShipyardNeoSandboxRuntimePlugin(Star):
    def __init__(self, context: Context, config=None) -> None:
        super().__init__(context)
        self.provider = ShipyardNeoSandboxProvider()
        self.provider.plugin_config = config or {}
        register_sandbox_provider(self.provider, replace=True)
        for tool in (
            BrowserExecTool(),
            BrowserBatchExecTool(),
            RunBrowserSkillTool(),
            GetExecutionHistoryTool(),
            AnnotateExecutionTool(),
            CreateSkillPayloadTool(),
            GetSkillPayloadTool(),
            CreateSkillCandidateTool(),
            ListSkillCandidatesTool(),
            EvaluateSkillCandidateTool(),
            PromoteSkillCandidateTool(),
            ListSkillReleasesTool(),
            RollbackSkillReleaseTool(),
            SyncSkillReleaseTool(),
        ):
            llm_tools.func_list.append(tool)

    async def terminate(self) -> None:
        for tool_name in self.provider.tool_names:
            llm_tools.remove_func(tool_name)
        unregister_sandbox_provider(self.provider.provider_id, force=True)
