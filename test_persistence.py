import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from data.plugins.astrbot_sandbox_shipyard_neo import main as plugin_main
from data.plugins.astrbot_sandbox_shipyard_neo import provider as provider_module
from data.plugins.astrbot_sandbox_shipyard_neo.booters import shipyard_neo
from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo_endpoint import (
    DEFAULT_SHIPYARD_NEO_ENDPOINT,
    SHIPYARD_NEO_AUTO_ENDPOINT,
    is_shipyard_neo_auto_endpoint,
    normalize_shipyard_neo_endpoint,
)
from data.plugins.astrbot_sandbox_shipyard_neo.tools.shipyard_neo import (
    SHIPYARD_NEO_TOOL_MODULE_PREFIX,
)


class FakeReadySandbox:
    def __init__(
        self,
        sandbox_id: str = "sbx_fake",
        profile: str = "python-default",
        capabilities: list[str] | None = None,
    ):
        self.id = sandbox_id
        self.profile = profile
        self.capabilities = [] if capabilities is None else capabilities
        self.status = SimpleNamespace(value="ready")
        self.shell = SimpleNamespace()
        self.filesystem = SimpleNamespace()
        self.python = SimpleNamespace()
        self.browser = SimpleNamespace()

    async def refresh(self):
        return None


def test_shipyard_neo_provider_connect_info_tracks_sandbox_id():
    provider = provider_module.ShipyardNeoSandboxProvider()
    assert (
        provider_module.ShipyardNeoSandboxProvider.supports_persistent_reconnect is True
    )

    info = provider.build_connect_info(
        "Named",
        {
            "endpoint_url": "https://example.com",
            "profile": "python-default",
            "persistent_name": "neo-1",
            "sandbox_id": "sbx_123",
        },
    )

    assert info["persistent_name"] == "neo-1"
    assert info["sandbox_id"] == "sbx_123"


def test_shipyard_neo_provider_connect_info_uses_astrbot_sandbox_id_for_persistent_name():
    provider = provider_module.ShipyardNeoSandboxProvider()

    info = provider.build_connect_info(
        "display-name",
        {"sandbox_id": "neo-runtime-1"},
    )

    assert info["name"] == "display-name"
    assert info["persistent_name"] == "neo-runtime-1"
    assert info["sandbox_id"] == "neo-runtime-1"


def test_shipyard_neo_provider_tool_names_derive_from_registered_tool_classes():
    from data.plugins.astrbot_sandbox_shipyard_neo.tools.shipyard_neo import (
        SHIPYARD_NEO_TOOL_CLASSES,
        build_shipyard_neo_tools,
    )

    assert provider_module.ShipyardNeoSandboxProvider.tool_names == {
        tool_cls.name for tool_cls in SHIPYARD_NEO_TOOL_CLASSES
    }
    assert provider_module.ShipyardNeoSandboxProvider.tool_names == {
        tool.name for tool in build_shipyard_neo_tools()
    }


def test_shipyard_neo_provider_defaults_to_local_endpoint_when_unconfigured():
    provider = provider_module.ShipyardNeoSandboxProvider()

    config = provider.build_create_config(
        SimpleNamespace(get_config=lambda umo: {"provider_settings": {"sandbox": {}}}),
        "dashboard",
    )

    assert config["endpoint_url"] == DEFAULT_SHIPYARD_NEO_ENDPOINT
    assert config["access_token"] == ""
    assert config["is_auto_mode"] is None


@pytest.mark.parametrize(
    ("raw_autostart", "endpoint", "expected"),
    [
        ("default", DEFAULT_SHIPYARD_NEO_ENDPOINT, None),
        ("default", "http://127.0.0.1:9000", None),
        ("true", "http://127.0.0.1:9000", True),
        ("false", DEFAULT_SHIPYARD_NEO_ENDPOINT, False),
        (" TRUE ", "http://127.0.0.1:9000", True),
    ],
)
def test_shipyard_neo_provider_resolves_autostart_setting(
    raw_autostart,
    endpoint,
    expected,
    monkeypatch,
):
    monkeypatch.setattr(provider_module, "_discover_bay_credentials", lambda _: "token")
    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": endpoint,
                    "shipyard_neo_autostart": raw_autostart,
                }
            }
        }
    )

    config = provider.build_create_config(context, "dashboard")

    assert config["is_auto_mode"] is expected


def test_shipyard_neo_provider_rejects_invalid_autostart_setting():
    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {"sandbox": {"shipyard_neo_autostart": "sometimes"}}
        }
    )

    with pytest.raises(ValueError, match="shipyard_neo_autostart"):
        provider.build_create_config(context, "dashboard")


@pytest.mark.parametrize(
    ("endpoint", "is_auto_mode", "expected"),
    [
        (DEFAULT_SHIPYARD_NEO_ENDPOINT, None, True),
        ("http://127.0.0.1:9000", None, False),
        ("http://127.0.0.1:9000", True, True),
        (DEFAULT_SHIPYARD_NEO_ENDPOINT, False, False),
    ],
)
def test_shipyard_neo_booter_resolves_auto_start_mode(
    endpoint,
    is_auto_mode,
    expected,
):
    assert (
        shipyard_neo.should_auto_start_shipyard_neo(endpoint, is_auto_mode) is expected
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        (DEFAULT_SHIPYARD_NEO_ENDPOINT, True),
        ("http://127.0.0.1:9000", False),
    ],
)
async def test_shipyard_neo_provider_preserves_autostart_auto_detect_when_omitted(
    endpoint,
    expected,
    monkeypatch,
):
    monkeypatch.setattr(provider_module, "_discover_bay_credentials", lambda _: "token")
    recorded = {}

    class FakeBooter:
        DEFAULT_PROFILE = shipyard_neo.ShipyardNeoBooter.DEFAULT_PROFILE

        def __init__(self, **kwargs):
            recorded.update(kwargs)

        async def boot(self, session_id: str):
            recorded["boot_session_id"] = session_id

    monkeypatch.setattr(provider_module, "ShipyardNeoBooter", FakeBooter)
    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": endpoint,
                }
            }
        }
    )

    config = provider.build_create_config(context, "dashboard")
    await provider.create_booter(context, "dashboard", "neo-1", config)

    assert recorded["is_auto_mode"] is None
    assert (
        shipyard_neo.should_auto_start_shipyard_neo(
            recorded["endpoint_url"],
            recorded["is_auto_mode"],
        )
        is expected
    )


@pytest.mark.asyncio
async def test_shipyard_neo_provider_autostart_false_disables_default_endpoint_autostart(
    monkeypatch,
):
    recorded = {}

    class FakeBayManager:
        def __init__(self, **kwargs):
            raise AssertionError("autostart=false must not launch Bay")

    class FakeClient:
        def __init__(self, **kwargs):
            recorded["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def list_profiles(self):
            return SimpleNamespace(items=[])

        async def create_sandbox(self, *, profile: str, ttl: int):
            del profile, ttl
            return FakeReadySandbox("sbx_no_autostart")

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager.BayContainerManager",
        FakeBayManager,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        FakeClient,
    )

    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": DEFAULT_SHIPYARD_NEO_ENDPOINT,
                    "shipyard_neo_access_token": "configured-token",
                    "shipyard_neo_autostart": "false",
                }
            }
        }
    )
    config = provider.build_create_config(context, "dashboard")

    await provider.create_booter(context, "dashboard", "neo-1", config)

    assert recorded["client_kwargs"] == {
        "endpoint_url": DEFAULT_SHIPYARD_NEO_ENDPOINT,
        "access_token": "configured-token",
    }


@pytest.mark.parametrize(
    "endpoint_value, expected_endpoint, expected_auto",
    [
        ("http://localhost:8114", DEFAULT_SHIPYARD_NEO_ENDPOINT, True),
        ("http://127.0.0.1:8114/", DEFAULT_SHIPYARD_NEO_ENDPOINT, True),
        ("https://127.0.0.1:8114", "https://127.0.0.1:8114", False),
        ("http://127.0.0.1:9000", "http://127.0.0.1:9000", False),
    ],
)
def test_shipyard_neo_provider_normalizes_localhost_and_rejects_non_auto_endpoints(
    endpoint_value,
    expected_endpoint,
    expected_auto,
    monkeypatch,
):
    discovered: list[str] = []

    def fake_discover(endpoint: str) -> str:
        discovered.append(endpoint)
        return "discovered-token"

    monkeypatch.setattr(provider_module, "_discover_bay_credentials", fake_discover)
    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": endpoint_value,
                }
            }
        }
    )

    config = provider.build_create_config(context, "dashboard")

    assert config["endpoint_url"] == expected_endpoint
    assert config["access_token"] == ("" if expected_auto else "discovered-token")
    assert discovered == ([] if expected_auto else [expected_endpoint])
    assert is_shipyard_neo_auto_endpoint(config["endpoint_url"]) is expected_auto


@pytest.mark.parametrize(
    "endpoint_value, expected_endpoint, expected_auto",
    [
        (None, DEFAULT_SHIPYARD_NEO_ENDPOINT, True),
        (SHIPYARD_NEO_AUTO_ENDPOINT, DEFAULT_SHIPYARD_NEO_ENDPOINT, True),
        (" http://localhost:8114/ ", DEFAULT_SHIPYARD_NEO_ENDPOINT, True),
        ("http://127.0.0.1:9000", "http://127.0.0.1:9000", False),
    ],
)
def test_shipyard_neo_endpoint_helper_centralizes_normalization(
    endpoint_value, expected_endpoint, expected_auto
):
    normalized = normalize_shipyard_neo_endpoint(endpoint_value)

    assert normalized == expected_endpoint
    assert is_shipyard_neo_auto_endpoint(normalized) is expected_auto


@pytest.mark.asyncio
async def test_shipyard_neo_terminate_detaches_even_if_cleanup_fails(monkeypatch):
    calls = []

    class FakeProvider:
        provider_id = "shipyard_neo"

    async def fake_cleanup(provider_id):
        calls.append(("cleanup", provider_id))
        raise RuntimeError("cleanup failed")

    def fake_detach(provider_id):
        calls.append(("detach", provider_id))

    def fake_unregister():
        calls.append(("unregister", SHIPYARD_NEO_TOOL_MODULE_PREFIX))
        return ["astrbot_execute_browser"]

    monkeypatch.setattr(plugin_main, "cleanup_sandbox_provider", fake_cleanup)
    monkeypatch.setattr(plugin_main, "detach_sandbox_provider", fake_detach)
    monkeypatch.setattr(
        plugin_main, "_unregister_shipyard_neo_builtin_tools", fake_unregister
    )

    plugin = plugin_main.ShipyardNeoSandboxRuntimePlugin.__new__(
        plugin_main.ShipyardNeoSandboxRuntimePlugin
    )
    plugin.provider = FakeProvider()

    with pytest.raises(RuntimeError, match="cleanup failed"):
        await plugin.terminate()

    assert calls == [
        ("cleanup", "shipyard_neo"),
        ("detach", "shipyard_neo"),
        ("unregister", SHIPYARD_NEO_TOOL_MODULE_PREFIX),
    ]


@pytest.mark.asyncio
async def test_shipyard_neo_terminate_detaches_on_successful_cleanup(monkeypatch):
    calls = []

    class FakeProvider:
        provider_id = "shipyard_neo"

    async def fake_cleanup(provider_id):
        calls.append(("cleanup", provider_id))

    def fake_detach(provider_id):
        calls.append(("detach", provider_id))

    def fake_unregister():
        calls.append(("unregister", SHIPYARD_NEO_TOOL_MODULE_PREFIX))
        return ["astrbot_execute_browser"]

    monkeypatch.setattr(plugin_main, "cleanup_sandbox_provider", fake_cleanup)
    monkeypatch.setattr(plugin_main, "detach_sandbox_provider", fake_detach)
    monkeypatch.setattr(
        plugin_main, "_unregister_shipyard_neo_builtin_tools", fake_unregister
    )

    plugin = plugin_main.ShipyardNeoSandboxRuntimePlugin.__new__(
        plugin_main.ShipyardNeoSandboxRuntimePlugin
    )
    plugin.provider = FakeProvider()

    await plugin.terminate()

    assert calls == [
        ("cleanup", "shipyard_neo"),
        ("detach", "shipyard_neo"),
        ("unregister", SHIPYARD_NEO_TOOL_MODULE_PREFIX),
    ]


def test_shipyard_neo_finalize_clears_builtin_tool_cache(monkeypatch):
    calls = []

    class FakeToolManager:
        def clear_builtin_tool_cache_by_module_prefix(self, module_prefix):
            calls.append(("clear_cache", module_prefix))
            return ["astrbot_execute_browser"]

    class FakeContext:
        def get_llm_tool_manager(self):
            return FakeToolManager()

    class FakeProvider:
        provider_id = "shipyard_neo"

    def fake_detach(provider_id):
        calls.append(("detach", provider_id))

    def fake_unregister():
        calls.append(("unregister", SHIPYARD_NEO_TOOL_MODULE_PREFIX))
        return ["astrbot_execute_browser"]

    monkeypatch.setattr(plugin_main, "detach_sandbox_provider", fake_detach)
    monkeypatch.setattr(
        plugin_main, "_unregister_shipyard_neo_builtin_tools", fake_unregister
    )

    plugin_main._finalize_shipyard_neo_provider("shipyard_neo", FakeContext())

    assert calls == [
        ("detach", "shipyard_neo"),
        ("clear_cache", SHIPYARD_NEO_TOOL_MODULE_PREFIX),
        ("unregister", SHIPYARD_NEO_TOOL_MODULE_PREFIX),
    ]


def test_shipyard_neo_finalize_swallows_builtin_tool_cache_errors(monkeypatch):
    calls = []

    class ErrorToolManager:
        def clear_builtin_tool_cache_by_module_prefix(self, module_prefix):
            calls.append(("clear_cache_error", module_prefix))
            raise RuntimeError("cache clear failed")

    class FakeContext:
        def get_llm_tool_manager(self):
            return ErrorToolManager()

    def fake_detach(provider_id):
        calls.append(("detach", provider_id))

    def fake_unregister():
        calls.append(("unregister", SHIPYARD_NEO_TOOL_MODULE_PREFIX))
        return ["astrbot_execute_browser"]

    monkeypatch.setattr(plugin_main, "detach_sandbox_provider", fake_detach)
    monkeypatch.setattr(
        plugin_main, "_unregister_shipyard_neo_builtin_tools", fake_unregister
    )

    plugin_main._finalize_shipyard_neo_provider("shipyard_neo", FakeContext())

    assert calls == [
        ("detach", "shipyard_neo"),
        ("clear_cache_error", SHIPYARD_NEO_TOOL_MODULE_PREFIX),
        ("unregister", SHIPYARD_NEO_TOOL_MODULE_PREFIX),
    ]


def test_shipyard_neo_unregister_builtin_tools_uses_compatibility_fallback(
    monkeypatch,
):
    class FakeTool:
        __module__ = f"{SHIPYARD_NEO_TOOL_MODULE_PREFIX}.browser"

    classes_by_name = {"astrbot_execute_browser": FakeTool}
    names_by_class = {FakeTool: "astrbot_execute_browser"}
    config_rules = {"astrbot_execute_browser": object()}

    monkeypatch.setattr(
        plugin_main.tool_registry,
        "unregister_builtin_tools_by_module_prefix",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        plugin_main.tool_registry,
        "iter_builtin_tool_classes",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        plugin_main.tool_registry,
        "unregister_builtin_tool_class",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        plugin_main.tool_registry,
        "_builtin_tool_classes_by_name",
        classes_by_name,
        raising=False,
    )
    monkeypatch.setattr(
        plugin_main.tool_registry,
        "_builtin_tool_names_by_class",
        names_by_class,
        raising=False,
    )
    monkeypatch.setattr(
        plugin_main.tool_registry,
        "_BUILTIN_TOOL_CONFIG_RULES",
        config_rules,
        raising=False,
    )

    removed = plugin_main._unregister_shipyard_neo_builtin_tools()

    assert removed == ["astrbot_execute_browser"]
    assert classes_by_name == {}
    assert names_by_class == {}
    assert config_rules == {}


@pytest.mark.asyncio
async def test_shipyard_neo_terminate_logs_unregister_failure_without_masking_cleanup(
    monkeypatch,
):
    calls = []

    class FakeProvider:
        provider_id = "shipyard_neo"

    async def fake_cleanup(provider_id):
        calls.append(("cleanup", provider_id))

    def fake_detach(provider_id):
        calls.append(("detach", provider_id))

    def fake_unregister():
        calls.append(("unregister", SHIPYARD_NEO_TOOL_MODULE_PREFIX))
        raise RuntimeError("unregister failed")

    warnings = []

    def fake_warning(*args, **kwargs):
        class FakeWarningRecord:
            exc_info = kwargs.get("exc_info")

            def getMessage(self):
                message = str(args[0])
                if len(args) > 1:
                    return message % args[1:]
                return message

        warnings.append(FakeWarningRecord())

    monkeypatch.setattr(plugin_main, "cleanup_sandbox_provider", fake_cleanup)
    monkeypatch.setattr(plugin_main, "detach_sandbox_provider", fake_detach)
    monkeypatch.setattr(
        plugin_main, "_unregister_shipyard_neo_builtin_tools", fake_unregister
    )
    monkeypatch.setattr(plugin_main.logger, "warning", fake_warning)

    plugin = plugin_main.ShipyardNeoSandboxRuntimePlugin.__new__(
        plugin_main.ShipyardNeoSandboxRuntimePlugin
    )
    plugin.provider = FakeProvider()

    await plugin.terminate()

    assert calls == [
        ("cleanup", "shipyard_neo"),
        ("detach", "shipyard_neo"),
        ("unregister", SHIPYARD_NEO_TOOL_MODULE_PREFIX),
    ]
    assert len(warnings) == 1
    warning = warnings[0]
    assert "Shipyard Neo builtin tool cleanup failed" in warning.getMessage()
    assert warning.exc_info


def test_shipyard_neo_provider_update_connect_info_populates_legacy_persistent_name_from_sandbox_id():
    provider = provider_module.ShipyardNeoSandboxProvider()

    updated = provider.update_connect_info(
        {"sandbox_id": "neo-runtime-1", "connect_info": {"name": "Legacy"}},
        sandbox_name="Renamed",
    )

    assert updated["name"] == "Renamed"
    assert updated["persistent_name"] == "neo-runtime-1"


def test_shipyard_neo_provider_update_connect_info_preserves_existing_persistent_name():
    provider = provider_module.ShipyardNeoSandboxProvider()

    updated = provider.update_connect_info(
        {
            "connect_info": {
                "name": "Legacy",
                "persistent_name": "Original",
            }
        },
        sandbox_name="Renamed",
    )

    assert updated["name"] == "Renamed"
    assert updated["persistent_name"] == "Original"


def test_shipyard_neo_provider_updates_runtime_sandbox_id_after_boot():
    provider = provider_module.ShipyardNeoSandboxProvider()
    booter = SimpleNamespace(sandbox=SimpleNamespace(id="bay-sbx-1"))

    updated = provider.update_connect_info_after_boot(
        {
            "sandbox_id": "shipyard_neo-1",
            "connect_info": {
                "name": "Neo",
                "persistent_name": "shipyard_neo-1",
                "sandbox_id": "shipyard_neo-1",
            },
        },
        booter,
    )

    assert updated["sandbox_id"] == "bay-sbx-1"
    assert updated["persistent_name"] == "shipyard_neo-1"


@pytest.mark.asyncio
async def test_shipyard_neo_provider_passes_reconnect_metadata(monkeypatch):
    recorded = {}

    class FakeBooter:
        def __init__(self, **kwargs):
            recorded.update(kwargs)
            self.sandbox_id = kwargs.get("sandbox_id")

        async def boot(self, session_id: str):
            recorded["boot_session_id"] = session_id

    monkeypatch.setattr(provider_module, "ShipyardNeoBooter", FakeBooter)

    provider = provider_module.ShipyardNeoSandboxProvider()
    booter = await provider.create_booter(
        context=SimpleNamespace(),
        session_id="dashboard",
        sandbox_id="neo-1",
        config={
            "endpoint_url": "https://example.com",
            "access_token": "token",
            "profile": "python-default",
            "ttl": 3600,
        },
    )

    assert recorded["persistent"] is True
    assert recorded["persistent_name"] == "neo-1"
    assert recorded["resume"] is False
    assert recorded["sandbox_id"] == "neo-1"
    for key in ("ttl", "endpoint_url", "profile"):
        assert key in recorded
    assert getattr(booter, "sandbox_id") == "neo-1"


@pytest.mark.asyncio
async def test_shipyard_neo_provider_uses_config_overrides_without_keyword_conflicts(
    monkeypatch,
):
    recorded = {}

    class FakeBooter:
        def __init__(self, **kwargs):
            recorded.update(kwargs)

        async def boot(self, session_id: str):
            recorded["boot_session_id"] = session_id

    monkeypatch.setattr(provider_module, "ShipyardNeoBooter", FakeBooter)

    provider = provider_module.ShipyardNeoSandboxProvider()
    await provider.create_booter(
        context=SimpleNamespace(),
        session_id="dashboard",
        sandbox_id="neo-2",
        config={
            "endpoint_url": "https://example.com",
            "access_token": "token",
            "profile": "python-default",
            "ttl": 3600,
            "persistent_name": " neo-custom ",
            "resume": True,
            "sandbox_id": "sbx_existing",
        },
    )

    assert recorded["persistent"] is True
    assert recorded["persistent_name"] == "neo-custom"
    assert recorded["resume"] is True
    assert recorded["existing_sandbox_id"] == "sbx_existing"


@pytest.mark.asyncio
async def test_shipyard_neo_booter_resume_does_not_create_when_sandbox_missing(
    monkeypatch,
):
    from shipyard_neo.errors import NotFoundError

    from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo import (
        ShipyardNeoBooter,
    )

    recorded = []

    class FakeClient:
        async def __aenter__(self):
            return self

        async def get_sandbox(self, sandbox_id: str):
            raise NotFoundError()

        async def create_sandbox(self, *, profile: str, ttl: int):
            raise AssertionError("resume path must not create a new sandbox")

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        lambda **kwargs: FakeClient(),
    )

    async def fake_resolve_profile(self, client):
        return "python-default"

    monkeypatch.setattr(ShipyardNeoBooter, "_resolve_profile", fake_resolve_profile)

    booter = ShipyardNeoBooter(
        endpoint_url="https://example.com",
        access_token="token",
        resume=True,
        existing_sandbox_id="stale_sbx",
        sandbox_id="neo-1",
    )

    with pytest.raises(RuntimeError, match="could not be resumed"):
        await booter.boot("ignored")

    assert recorded == []


@pytest.mark.asyncio
async def test_shipyard_neo_auto_mode_generates_token_for_bay_and_client(monkeypatch):
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo import (
        SHIPYARD_NEO_AUTO_ENDPOINT,
        ShipyardNeoBooter,
    )

    recorded = {}

    class FakeBayManager:
        def __init__(self, *, access_token: str):
            recorded["manager_token"] = access_token

        async def ensure_running(self):
            return "http://127.0.0.1:8114"

        async def wait_healthy(self):
            return None

        async def read_credentials(self):
            raise AssertionError("random token should avoid reading credentials")

    class FakeClient:
        def __init__(self, **kwargs):
            recorded["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def list_profiles(self):
            return SimpleNamespace(items=[])

        async def create_sandbox(self, *, profile: str, ttl: int):
            return FakeReadySandbox("sbx_generated")

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager.BayContainerManager",
        FakeBayManager,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        FakeClient,
    )
    booter = ShipyardNeoBooter(
        endpoint_url=SHIPYARD_NEO_AUTO_ENDPOINT,
        access_token="",
    )

    await booter.boot("ignored")

    assert recorded["manager_token"]
    assert recorded["client_kwargs"] == {
        "endpoint_url": "http://127.0.0.1:8114",
        "access_token": recorded["manager_token"],
    }


@pytest.mark.asyncio
async def test_shipyard_neo_local_default_triggers_auto_start(monkeypatch):
    recorded = {}

    class FakeBayManager:
        def __init__(self, *, access_token: str):
            recorded["manager_token"] = access_token

        async def ensure_running(self):
            return "http://127.0.0.1:8114"

        async def wait_healthy(self):
            return None

    class FakeClient:
        def __init__(self, **kwargs):
            recorded["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def list_profiles(self):
            return SimpleNamespace(items=[])

        async def create_sandbox(self, *, profile: str, ttl: int):
            del profile, ttl
            return FakeReadySandbox("sbx_local_default")

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager.BayContainerManager",
        FakeBayManager,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        FakeClient,
    )

    booter = shipyard_neo.ShipyardNeoBooter(
        endpoint_url=DEFAULT_SHIPYARD_NEO_ENDPOINT,
        access_token="",
    )

    await booter.boot("ignored")

    assert recorded["manager_token"]
    assert recorded["client_kwargs"] == {
        "endpoint_url": "http://127.0.0.1:8114",
        "access_token": recorded["manager_token"],
    }


@pytest.mark.asyncio
async def test_shipyard_neo_auto_mode_reuses_configured_token(monkeypatch):
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo import (
        SHIPYARD_NEO_AUTO_ENDPOINT,
        ShipyardNeoBooter,
    )

    recorded = {}

    class FakeBayManager:
        def __init__(self, *, access_token: str):
            recorded["manager_token"] = access_token

        async def ensure_running(self):
            return "http://127.0.0.1:8114"

        async def wait_healthy(self):
            return None

        async def read_credentials(self):
            raise AssertionError("configured token should avoid reading credentials")

    class FakeClient:
        def __init__(self, **kwargs):
            recorded["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def list_profiles(self):
            return SimpleNamespace(items=[])

        async def create_sandbox(self, *, profile: str, ttl: int):
            return FakeReadySandbox("sbx_configured")

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager.BayContainerManager",
        FakeBayManager,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        FakeClient,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.secrets.token_urlsafe",
        lambda n: (_ for _ in ()).throw(AssertionError("token should be reused")),
    )

    booter = ShipyardNeoBooter(
        endpoint_url=SHIPYARD_NEO_AUTO_ENDPOINT,
        access_token="configured-token",
    )

    await booter.boot("ignored")

    assert recorded["manager_token"] == "configured-token"
    assert recorded["client_kwargs"] == {
        "endpoint_url": "http://127.0.0.1:8114",
        "access_token": "configured-token",
    }


@pytest.mark.parametrize(
    "endpoint_value, access_token, expected_endpoint, expected_token",
    [
        (None, "", DEFAULT_SHIPYARD_NEO_ENDPOINT, ""),
        (
            SHIPYARD_NEO_AUTO_ENDPOINT,
            "",
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "",
        ),
        ("   ", "", DEFAULT_SHIPYARD_NEO_ENDPOINT, ""),
        (
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "",
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "",
        ),
        (
            SHIPYARD_NEO_AUTO_ENDPOINT,
            "pre-configured-token",
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "pre-configured-token",
        ),
        (
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "pre-configured-token",
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "pre-configured-token",
        ),
    ],
)
def test_shipyard_neo_provider_auto_like_endpoints_do_not_trigger_discovery(
    monkeypatch,
    endpoint_value,
    access_token,
    expected_endpoint,
    expected_token,
):
    def fail_discovery(endpoint: str):
        raise AssertionError(f"should not discover credentials for {endpoint}")

    monkeypatch.setattr(provider_module, "_discover_bay_credentials", fail_discovery)

    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": endpoint_value,
                    "shipyard_neo_access_token": access_token,
                }
            }
        }
    )

    config = provider.build_create_config(context, "dashboard")

    assert config["endpoint_url"] == expected_endpoint
    assert config["access_token"] == expected_token


def test_shipyard_neo_provider_rejects_non_string_endpoint():
    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": {"url": "http://127.0.0.1:8114"},
                }
            }
        }
    )

    with pytest.raises(TypeError, match="shipyard_neo_endpoint must be a string"):
        provider.build_create_config(context, "dashboard")


def test_shipyard_neo_provider_discovers_credentials_for_non_auto_endpoint(
    monkeypatch,
):
    recorded = {}

    def fake_discover_bay_credentials(endpoint: str) -> str:
        recorded["endpoint"] = endpoint
        return "discovered-token"

    monkeypatch.setattr(
        provider_module,
        "_discover_bay_credentials",
        fake_discover_bay_credentials,
    )

    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": " https://bay.example.com ",
                    "shipyard_neo_access_token": "",
                }
            }
        }
    )

    config = provider.build_create_config(context, "dashboard")

    assert recorded["endpoint"] == "https://bay.example.com"
    assert config["endpoint_url"] == "https://bay.example.com"
    assert config["access_token"] == "discovered-token"


def test_shipyard_neo_provider_rejects_non_string_access_token():
    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_access_token": {"token": "secret"},
                }
            }
        }
    )

    with pytest.raises(TypeError, match="shipyard_neo_access_token must be a string"):
        provider.build_create_config(context, "dashboard")


def test_shipyard_neo_provider_strips_access_token_without_discovery(monkeypatch):
    def fail_discovery(endpoint: str):
        raise AssertionError(f"should not discover credentials for {endpoint}")

    monkeypatch.setattr(provider_module, "_discover_bay_credentials", fail_discovery)

    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": " https://bay.example.com ",
                    "shipyard_neo_access_token": " configured-token ",
                }
            }
        }
    )

    config = provider.build_create_config(context, "dashboard")

    assert config["endpoint_url"] == "https://bay.example.com"
    assert config["access_token"] == "configured-token"


def _assert_core_bay_env(env: list[str]) -> None:
    assert "BAY_SECURITY__ALLOW_ANONYMOUS=false" in env
    assert "BAY_DATA_DIR=/app/data" in env
    assert "BAY_DOCKER__NETWORK=shipyard" in env
    assert any(entry.startswith("BAY_SERVER__HOST=") for entry in env)
    assert any(entry.startswith("BAY_SERVER__PORT=") for entry in env)


def test_bay_manager_omits_empty_api_key_env():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="")
    env = manager.build_container_env()

    _assert_core_bay_env(env)
    assert all(not entry.startswith("BAY_SECURITY__API_KEY=") for entry in env)


@pytest.mark.asyncio
async def test_shipyard_neo_provider_shortens_docker_unavailable_errors(monkeypatch):
    class FakeBooter:
        DEFAULT_PROFILE = "python-default"

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def boot(self, session_id):
            raise RuntimeError(
                "Failed to connect to Docker daemon. "
                "Ensure Docker is installed and running, or configure an explicit Bay endpoint."
            )

    monkeypatch.setattr(provider_module, "ShipyardNeoBooter", FakeBooter)

    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {"provider_settings": {"sandbox": {}}}
    )
    config = provider.build_create_config(context, "session-a")

    with pytest.raises(
        RuntimeError, match="^Docker is not installed or not running$"
    ) as excinfo:
        await provider.create_booter(context, "session-a", "neo-1", config)

    cause = excinfo.value.__cause__
    assert isinstance(cause, RuntimeError)
    assert str(cause).startswith("Failed to connect to Docker daemon. ")


def test_shipyard_neo_provider_does_not_overmatch_docker_errors():
    assert not provider_module._is_docker_unavailable_error(
        RuntimeError("Failed to create Docker network using /var/run/docker.sock")
    )


def test_bay_manager_includes_api_key_env_when_token_is_configured():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="token")
    env = manager.build_container_env()

    _assert_core_bay_env(env)
    assert "BAY_SECURITY__API_KEY=token" in env


def test_bay_manager_configures_pullable_default_profile_image():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BROWSER_PYTHON_PROFILE_ID,
        DEFAULT_BAY_PROFILES,
        DEFAULT_GULL_RUNTIME_IMAGE,
        DEFAULT_SHIP_RUNTIME_IMAGE,
        PYTHON_DEFAULT_PROFILE_ID,
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="token")
    env = manager.build_container_env()
    profiles_env = next(item for item in env if item.startswith("BAY_PROFILES="))

    profiles = json.loads(profiles_env.removeprefix("BAY_PROFILES="))

    assert profiles == DEFAULT_BAY_PROFILES
    assert profiles is not DEFAULT_BAY_PROFILES

    python_profile = next(
        item for item in profiles if item["id"] == PYTHON_DEFAULT_PROFILE_ID
    )
    browser_profile = next(
        item for item in profiles if item["id"] == BROWSER_PYTHON_PROFILE_ID
    )

    assert python_profile["image"] == DEFAULT_SHIP_RUNTIME_IMAGE
    assert python_profile["resources"] == {"cpus": 1.0, "memory": "1g"}
    assert python_profile["capabilities"] == ["filesystem", "shell", "python"]
    assert python_profile["idle_timeout"] == 1800

    assert browser_profile["description"] == "Browser automation with Python backend"
    assert browser_profile["idle_timeout"] == 1800
    assert browser_profile["containers"] == [
        {
            "name": "ship",
            "image": DEFAULT_SHIP_RUNTIME_IMAGE,
            "runtime_type": "ship",
            "runtime_port": 8123,
            "resources": {"cpus": 1.0, "memory": "1g"},
            "capabilities": ["filesystem", "shell", "python"],
            "primary_for": ["filesystem", "shell", "python"],
            "env": {},
        },
        {
            "name": "browser",
            "image": DEFAULT_GULL_RUNTIME_IMAGE,
            "runtime_type": "gull",
            "runtime_port": 8115,
            "resources": {"cpus": 1.0, "memory": "2g"},
            "capabilities": ["browser"],
            "env": {},
        },
    ]
    assert sorted(
        capability
        for container in browser_profile["containers"]
        for capability in container["capabilities"]
    ) == [
        "browser",
        "filesystem",
        "python",
        "shell",
    ]


def test_docs_reference_default_bay_profile_ids():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BROWSER_PYTHON_PROFILE_ID,
        PYTHON_DEFAULT_PROFILE_ID,
    )

    readme = Path("README.md").read_text(encoding="utf-8")
    readme_cn = Path("README_cn.md").read_text(encoding="utf-8")
    schema = Path("_conf_schema.json").read_text(encoding="utf-8")

    for content in (readme, readme_cn, schema):
        assert PYTHON_DEFAULT_PROFILE_ID in content
        assert BROWSER_PYTHON_PROFILE_ID in content


def test_shipyard_neo_browser_property_reports_missing_capability():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo import (
        ShipyardNeoBooter,
    )

    booter = ShipyardNeoBooter(endpoint_url="https://example.com", access_token="token")
    booter._sandbox = FakeReadySandbox(capabilities=["filesystem", "shell", "python"])

    with pytest.raises(RuntimeError, match="does not include browser capability"):
        booter.browser


@pytest.mark.asyncio
async def test_shipyard_neo_resolve_profile_prefers_browser_python():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo import (
        ShipyardNeoBooter,
    )

    class FakeClient:
        async def list_profiles(self):
            return SimpleNamespace(
                items=[
                    SimpleNamespace(
                        id="python-default",
                        capabilities=["filesystem", "shell", "python"],
                    ),
                    SimpleNamespace(
                        id="browser-python",
                        capabilities=["filesystem", "shell", "python", "browser"],
                    ),
                ]
            )

    booter = ShipyardNeoBooter(endpoint_url="https://example.com", access_token="token")

    assert await booter._resolve_profile(FakeClient()) == "browser-python"


def test_bay_manager_detects_mismatched_existing_container_env():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="token")

    assert manager.container_env_matches({"Config": {"Env": []}}) is False


def test_bay_manager_accepts_matching_existing_container_env():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="token")

    assert (
        manager.container_env_matches(
            {
                "Config": {"Env": manager.build_container_env()},
                "HostConfig": {"NetworkMode": "shipyard"},
            }
        )
        is True
    )


def test_bay_manager_matches_without_access_token():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="")
    env = manager.build_container_env()

    assert "BAY_SECURITY__API_KEY=" not in env
    assert (
        manager.container_env_matches(
            {"Config": {"Env": env}, "HostConfig": {"NetworkMode": "shipyard"}}
        )
        is True
    )


def test_bay_manager_rejects_different_api_key():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="new-token")
    desired_env = manager.build_container_env()

    # Simulate an existing container with an old API key
    stale_env = [
        item for item in desired_env if not item.startswith("BAY_SECURITY__API_KEY=")
    ]
    stale_env.append("BAY_SECURITY__API_KEY=old-token")

    assert (
        manager.container_env_matches(
            {
                "Config": {"Env": stale_env},
                "HostConfig": {"NetworkMode": "shipyard"},
            }
        )
        is False
    )


@pytest.mark.asyncio
async def test_shipyard_neo_boot_closes_client_when_readiness_fails(monkeypatch):
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo import (
        ShipyardNeoBooter,
    )

    calls = []

    class FakeClient:
        async def __aenter__(self):
            calls.append("enter")
            return self

        async def __aexit__(self, exc_type, exc, tb):
            calls.append(("exit", exc_type, exc))

        async def list_profiles(self):
            return SimpleNamespace(items=[])

        async def create_sandbox(self, *, profile: str, ttl: int):
            return FakeReadySandbox("failed_sbx")

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        lambda **kwargs: FakeClient(),
    )

    async def fail_readiness(self, sandbox):
        raise RuntimeError("sandbox failed")

    monkeypatch.setattr(ShipyardNeoBooter, "_wait_until_ready", fail_readiness)

    booter = ShipyardNeoBooter(
        endpoint_url="https://example.com",
        access_token="token",
    )

    with pytest.raises(RuntimeError, match="sandbox failed"):
        await booter.boot("ignored")

    assert calls[0] == "enter"
    exit_call = calls[1]
    assert exit_call[0] == "exit"
    assert exit_call[1] is RuntimeError
    assert isinstance(exit_call[2], RuntimeError)
    assert str(exit_call[2]) == "sandbox failed"
    assert booter.bay_client is None


@pytest.mark.asyncio
async def test_shipyard_neo_provider_reports_persistent_sandbox_exists(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))

        async def __aenter__(self):
            calls.append("enter")
            return self

        async def __aexit__(self, exc_type, exc, tb):
            calls.append("exit")

        async def get_sandbox(self, sandbox_id: str):
            calls.append(("get", sandbox_id))
            return object()

    monkeypatch.setattr(shipyard_neo, "BayClient", FakeClient)

    provider = provider_module.ShipyardNeoSandboxProvider()

    exists = await provider.check_persistent_sandbox_exists(
        {
            "connect_info": {
                "endpoint_url": "https://example.com",
                "access_token": "token",
                "sandbox_id": "sbx_123",
            }
        }
    )

    assert exists is True
    assert calls == [
        ("init", {"endpoint_url": "https://example.com", "access_token": "token"}),
        "enter",
        ("get", "sbx_123"),
        "exit",
    ]


@pytest.mark.asyncio
async def test_shipyard_neo_provider_reports_missing_persistent_sandbox(monkeypatch):
    from shipyard_neo.errors import NotFoundError

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get_sandbox(self, sandbox_id: str):
            raise NotFoundError()

    monkeypatch.setattr(shipyard_neo, "BayClient", lambda **kwargs: FakeClient())

    provider = provider_module.ShipyardNeoSandboxProvider()

    exists = await provider.check_persistent_sandbox_exists(
        {
            "connect_info": {
                "endpoint_url": "https://example.com",
                "access_token": "token",
                "sandbox_id": "sbx_123",
            }
        }
    )

    assert exists is False


@pytest.mark.asyncio
async def test_shipyard_neo_provider_uses_plugin_token_for_existence_check(
    monkeypatch,
):
    recorded = {}

    class FakeClient:
        def __init__(self, **kwargs):
            recorded.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get_sandbox(self, sandbox_id: str):
            return object()

    monkeypatch.setattr(shipyard_neo, "BayClient", FakeClient)

    provider = provider_module.ShipyardNeoSandboxProvider(
        plugin_config={"shipyard_neo_access_token": "plugin-token"}
    )

    exists = await provider.check_persistent_sandbox_exists(
        {
            "connect_info": {
                "endpoint_url": "https://example.com",
                "sandbox_id": "sbx_123",
            }
        }
    )

    assert exists is True
    assert recorded["access_token"] == "plugin-token"
