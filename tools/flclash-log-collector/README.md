# FlClash / Mihomo Log Collector

Windows 上运行的本地实时采集器，通过 Mihomo External Controller API 收集核心日志、活动连接和规则/代理组快照，并按日期保存为 JSONL。

> **隐私提醒：** 采集数据可能包含访问域名、目标 IP、来源 IP、进程名和流量信息。日志只写入本机目录；分享前请自行检查并脱敏。不要提交 `settings.json`、`FlClashLogs/` 或 `collector-startup.log`。

## 功能

- 通过 `/logs` WebSocket 订阅 Mihomo 核心日志。
- 通过 `/connections` WebSocket 采集活动连接，记录连接建立、更新和结束事件。
- 记录规则快照，以及经过筛选的代理组选择状态。
- WebSocket 断线后自动重连。
- 按本机日期写入 `FlClashLogs/YYYY-MM-DD.jsonl`。
- 不请求 `/configs`，避免读取订阅内容、节点凭据等配置秘密。

## 环境要求

- Windows 10/11
- Python 3.10 或更高版本
- FlClash/Mihomo 已运行，并启用本机 External Controller
- 本机控制器地址默认 `http://127.0.0.1:9090`

建议只将 External Controller 绑定到 `127.0.0.1`，不要为了采集器而开放到局域网或公网。

## 快速开始

1. 下载源码 ZIP，解压到一个独立文件夹。
2. 复制 `settings.example.json` 并命名为 `settings.json`。
3. 在本机编辑 `settings.json`，填写自己的 External Controller 密钥：

   ```json
   {
     "controller": "http://127.0.0.1:9090",
     "secret": "在这里填写本机控制器密钥",
     "connection_interval_ms": 250,
     "connection_snapshot_seconds": 5,
     "log_level": "debug",
     "context_refresh_seconds": 60,
     "output_dir": "FlClashLogs"
   }
   ```

4. 双击 `run.bat`。启动器会检测 Python 并在需要时安装 `websocket-client`。
5. 保持命令窗口运行即可持续采集；按 `Ctrl+C` 正常停止。

`settings.json` 已加入 `.gitignore`，不会被 Git 跟踪。不要将密钥粘贴到 Issue、Pull Request、聊天记录或提交信息中。

## 配置项

| 配置项 | 说明 | 默认值 |
|---|---|---|
| `controller` | 本机 Mihomo API 地址 | `http://127.0.0.1:9090` |
| `secret` | External Controller 密钥 | 空字符串 |
| `connection_interval_ms` | 连接 WebSocket 推送间隔（毫秒） | `250` |
| `connection_snapshot_seconds` | 同一连接流量更新的最小写入间隔 | `5` |
| `log_level` | `/logs` 订阅过滤级别 | `debug` |
| `context_refresh_seconds` | 规则和代理组快照刷新间隔 | `60` |
| `output_dir` | 日志输出目录 | `FlClashLogs` |

## 日志级别说明

`log_level` 只控制 API 订阅端的过滤级别，不能提高 Mihomo 核心本身的日志等级。核心全局 `log-level` 若设为 `info`，采集器无法获得核心没有产生的 `debug` 日志。需要更详细日志时，应在 FlClash 的有效配置中调整核心日志级别，并留意日志量增长。

## 采集边界

- 这是启动后的实时采集器，无法恢复启动前已经结束的连接。
- `/connections` 提供当前活动连接快照。短于推送间隔的连接仍可能漏采，不能保证绝对零遗漏。
- 采集的是 Mihomo 核心日志和连接信息，不包括 FlClash GUI 崩溃转储或 Windows 事件日志。
- 连接元数据可能包含个人隐私。请限制本地日志目录的访问权限，上传或分享前脱敏。

## 故障排查

- **Connection refused：** 确认 FlClash 正在运行，External Controller 已启用，地址与端口和 `settings.json` 一致。
- **HTTP 401：** 检查 `settings.json` 的 `secret` 是否与 FlClash 当前密钥完全一致。密钥区分大小写。
- **缺少 websocket-client：** 重新运行 `run.bat`，或执行 `py -3 -m pip install --user -r requirements.txt`。
- **启动失败：** 查看本目录的 `collector-startup.log`。分享诊断日志前请检查是否包含域名、IP 或其他隐私数据。

## API 依据

- [Mihomo API](https://wiki.metacubex.one/en/api/)
- [Mihomo General Configuration](https://wiki.metacubex.one/en/config/general/)