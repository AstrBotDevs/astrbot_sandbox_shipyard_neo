import asyncio

from astrbot.api import logger
from astrbot.api.star import Context, Star, register
from astrbot.core.computer.computer_client import (
    cleanup_sandbox_provider,
    detach_sandbox_provider,
    register_sandbox_provider,
)
from astrbot.core.tools.registry import unregister_builtin_tools_by_module_prefix

from .provider import ShipyardNeoSandboxProvider
from .tools.shipyard_neo import SHIPYARD_NEO_TOOL_MODULE_PREFIX


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
        )

    async def terminate(self) -> None:
        provider = getattr(self, "provider", None)
        provider_id = getattr(provider, "provider_id", None) if provider else None
        try:
            if provider_id:
                await cleanup_sandbox_provider(provider_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(
                "Shipyard Neo sandbox provider cleanup failed during termination: provider=%s",
                provider_id,
                exc_info=True,
            )
            raise
        finally:
            if provider_id:
                detach_sandbox_provider(provider_id)
                try:
                    removed = unregister_builtin_tools_by_module_prefix(
                        SHIPYARD_NEO_TOOL_MODULE_PREFIX
                    )
                except Exception:
                    logger.warning(
                        "Shipyard Neo builtin tool cleanup failed during termination: provider=%s",
                        provider_id,
                        exc_info=True,
                    )
                else:
                    if removed:
                        logger.info(
                            "Unregistered %d builtin tool(s) for Shipyard Neo: %s",
                            len(removed),
                            ", ".join(removed),
                        )
