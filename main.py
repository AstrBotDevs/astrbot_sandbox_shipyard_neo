from astrbot.api.star import Context, Star, register
from astrbot.core.computer.computer_client import (
    register_sandbox_provider,
    unregister_sandbox_provider,
)

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
    "astrbot_sandbox_shipyard_neo",
    "AstrBot Team",
    "为 AstrBot 提供 Shipyard Neo 沙盒运行时。",
    "0.1.0",
)
class ShipyardNeoSandboxRuntimePlugin(Star):
    def __init__(self, context: Context, config=None) -> None:
        super().__init__(context)
        self.provider = ShipyardNeoSandboxProvider(plugin_config=config)
        register_sandbox_provider(
            self.provider,
            replace=True,
            tools=[
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
            ],
        )

    async def terminate(self) -> None:
        unregister_sandbox_provider(self.provider.provider_id, force=True)
