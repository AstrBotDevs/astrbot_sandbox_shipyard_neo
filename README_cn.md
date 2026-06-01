# astrbot_sandbox_shipyard_neo

<div align="center">

<a href="./README.md">English</a> ｜ 简体中文

</div>

`astrbot_sandbox_shipyard_neo` 是 AstrBot 的 Shipyard Neo 沙盒驱动插件，也是更推荐的远程沙盒方案。它面向 Bay / Shipyard Neo 部署，除了 Shell、Python 和文件操作，还提供浏览器自动化和 Neo Skill 生命周期工具。

## 主要功能

1. 🛡️ 为 AstrBot 提供 `shipyard_neo` 沙盒驱动。
2. 💻 支持 Shell、Python、文件操作和浏览器能力。
3. 🌐 自动注册浏览器自动化工具。
4. 🧩 自动注册 Neo Skill 生命周期工具。
5. 📦 沙盒启动时会同步本地 AstrBot Skills。
6. 🔑 支持从 `credentials.json` 自动发现 Bay 凭据。

## 快速开始

### 安装插件

把插件克隆到 AstrBot 插件目录：

```bash
git clone https://github.com/zouyonghe/astrbot_sandbox_shipyard_neo.git data/plugins/astrbot_sandbox_shipyard_neo
```

然后重启 AstrBot，或在插件管理页重新加载插件。

### 启用 Shipyard Neo 沙盒驱动

在 AstrBot 仪表盘中启用沙盒模式，并选择 `shipyard_neo` 驱动。

对应配置路径：

- `provider_settings.computer_use_runtime`：`sandbox`
- `provider_settings.sandbox.booter`：`shipyard_neo`

## 配置项

| 键名 | 说明 |
| --- | --- |
| `shipyard_neo_endpoint` | Bay / Shipyard Neo API 地址，默认值为 `http://127.0.0.1:8114`。如果 AstrBot 和 Bay 跑在同一个 Docker 网络里，也可以填 Bay 的服务名。 |
| `shipyard_neo_access_token` | Bay API Key。留空时，本机自动启动会生成新密钥；外部端点会尝试自动发现。 |
| `shipyard_neo_profile` | 沙盒 profile。填写 `python-default` 时只启动基础 Python/Shell 沙箱；留空时，Bay 会自动选择最合适的 profile。浏览器自动化需要使用 `browser-python` 这类带浏览器能力的 profile。 |
| `shipyard_neo_ttl` | 沙盒 TTL，单位秒。 |

## 浏览器 Profile 拓扑

浏览器自动化运行在 Shipyard Neo 的 Gull 运行时中，不运行在执行 Shell 和 Python 的 Ship 容器里。本机自动启动 Bay 时会提供两个默认 profile：

| Profile | 容器 | 能力 |
| --- | --- | --- |
| `python-default` | `primary` (`ship`) | `filesystem`、`shell`、`python` |
| `browser-python` | `ship` (`ship`) + `browser` (`gull`) | `filesystem`、`shell`、`python`、`browser` |

当 `shipyard_neo_profile` 留空时，插件会向 Bay 查询可用 profiles，并优先选择包含 `browser` 能力的 profile。当它设置为 `python-default` 时，插件会直接使用该 profile。不要通过 `astrbot_execute_shell` 运行浏览器命令；请使用 `astrbot_execute_browser` 或 `astrbot_execute_browser_batch`，并且传入的命令不要带 `agent-browser` 前缀。

如果 AstrBot 和 Bay 运行在同一个 Docker Compose 网络中，请把 `shipyard_neo_endpoint` 配成 Bay 服务名，并确保 AstrBot 能访问对应网络。

自动发现凭据时会检查：

- `$BAY_DATA_DIR/credentials.json`
- 当前工作目录下的 `credentials.json`

## 适合场景

- 当你需要在沙盒内执行浏览器自动化时，优先使用这个插件。
- 它还会提供 Neo Skill 生命周期工具，例如 payload、candidate、release、rollback、sync。
- 浏览器能力是否可用，取决于所选 profile 是否包含提供 `browser` 能力的 Gull 容器。
- 插件销毁托管沙盒时会使用 `delete_sandbox=True` 清理资源。

## 依赖与限制

- 需要使用支持外部沙盒驱动插件的 AstrBot 版本。
- 依赖 `requirements.txt` 中的 `shipyard-neo-sdk`。
- 需要可用的 Bay / Shipyard Neo 服务。
- 需要有效的 Bay API Key，或者能被自动发现。
- 浏览器行为受 profile 和上游运行时支持情况影响。
- 如果只需要 Shell 或文件操作，经典 Shipyard 或 BoxLite 通常更轻。

## 排查建议

- 如果本机自动启动后没有可用端点，请确认 Docker 可用，并且默认地址还是 `http://127.0.0.1:8114`。
- 如果你不确定该填哪个 profile，可以留空让 Bay 自动选择。浏览器工作流应使用 `browser-python`，或其他包含提供 `browser` 能力的 `gull` 容器的 profile。
