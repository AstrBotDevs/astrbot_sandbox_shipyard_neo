import asyncio

from astrbot.api import logger
from astrbot.api.star import Context, Star, register
from astrbot.core.computer.computer_client import (
    cleanup_sandbox_provider,
    detach_sandbox_provider,
    register_sandbox_provider,
)
from astrbot.core.tools import registry as tool_registry

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
        tool_registry.register_builtin_tools_by_module_prefix(
            SHIPYARD_NEO_TOOL_MODULE_PREFIX
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
                _finalize_shipyard_neo_provider(
                    provider_id, getattr(self, "context", None)
                )

    def _clear_shipyard_neo_builtin_tool_cache(self) -> None:
        _clear_shipyard_neo_builtin_tool_cache(getattr(self, "context", None))


def _finalize_shipyard_neo_provider(provider_id: str, context: Context | None) -> None:
    detach_sandbox_provider(provider_id)
    _clear_shipyard_neo_builtin_tool_cache(context)
    try:
        removed = _unregister_shipyard_neo_builtin_tools()
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


def _clear_shipyard_neo_builtin_tool_cache(context: Context | None) -> None:
    get_tool_manager = getattr(context, "get_llm_tool_manager", None)
    if not callable(get_tool_manager):
        if context is None:
            logger.debug("Skipping Shipyard Neo builtin tool cache clear: no context")
        else:
            logger.debug(
                "Skipping Shipyard Neo builtin tool cache clear: context.get_llm_tool_manager is not callable (type=%s)",
                type(get_tool_manager).__name__,
            )
        return

    try:
        removed = get_tool_manager().clear_builtin_tool_cache_by_module_prefix(
            SHIPYARD_NEO_TOOL_MODULE_PREFIX
        )
    except Exception:
        logger.warning(
            "Shipyard Neo builtin tool cache cleanup failed during termination",
            exc_info=True,
        )
        return

    if removed:
        logger.info(
            "Cleared %d builtin tool cache entry(s) for Shipyard Neo: %s",
            len(removed),
            ", ".join(removed),
        )


def _unregister_shipyard_neo_builtin_tools() -> list[str]:
    return tool_registry.unregister_builtin_tools_by_module_prefix(
        SHIPYARD_NEO_TOOL_MODULE_PREFIX
    )
