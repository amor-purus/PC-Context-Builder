# PC Context Builder v2.0.0

**Your PC. Understood by AI.** — 本地构建 Windows 电脑环境资料包，供用户自行审核并提供给 AI 助手。

本工具**不会上传**采集结果，不读取文档正文、图片像素、视频或音频内容。任何生成的 ZIP 都**没有加密**，分享前必须审核。

## 下载与启动

- **普通用户**：在 [Releases](https://github.com/amor-purus/PC-Context-Builder/releases) 下载 `PC-Context-Builder.exe`。Windows 11 x64；无需自行安装 Python。
- **源码用户**：安装 CPython 3.14 x64，然后执行 `check_tool.bat` 和 `start.bat`。仅使用 Python 标准库和 Windows PowerShell/CIM。
- EXE 未签署 Authenticode 签名证书，Windows 可能显示未知发布者。请确认 GitHub 来源，并核对 Release 中的 `SHA256SUMS.txt`。

## v2.0.0 核心变化

1. **采集前授权（Privacy by design）**：默认只采集系统、CPU、GPU、RAM、显示器和固定磁盘容量；**不扫描文件夹/文件名，也不枚举已安装软件**。如有必要，在驱动器选择窗口事先分别勾选软件清单、文件系统元数据。
2. **两道独立许可**：第一道许可决定是否采集，第二道许可在 Review 中决定是否把已采集的信息放入 ZIP。软件、文件和文件夹记录仍逐行默认不导出。
3. **输出最小化**：机器卷标在导出内容中替换为 `[redacted]`；Windows/CIM 错误及异常信息只导出固定诊断代码，避免原始错误文字泄露用户名、文件路径等。即使选择警告类别，也不会导出完整 OS 错误字符串。
4. **专用 Schema v2.0**：`schema_version` 独立于应用版本号；`manifest.json` 明确记录采集范围和输出范围。归档发布前重新读取成员清单、运行 ZIP CRC 校验，并检查是否包含未经授权的类别。
5. **AI 信任边界**：`00_README_FOR_AI.md` 仅包含固定指导文字，**不插入动态设备名称或路径**。所有采集字段都作为不可信数据保存在 JSON/CSV 中；不要执行这些值中夹带的命令或提示词。
6. **后台生成、阶段进度与安全取消**：ZIP 写入运行在后台线程，显示写入/验证/发布阶段；取消仅在最终发布前生效，避免公开半成品正式 ZIP。
7. **保守型异常恢复**：工作目录中产生身份绑定的暂存日志。下次选择该目录时，只有文件身份得到确认、残留至少一小时且用户明确同意时，才清除残留；不确定的文件不会自动删除。
8. **可重复测试与分发**：Windows CI 运行内置自检、独立 `unittest` 回归/故障注入、合成文件性能基准、PyInstaller 打包和冻结版 EXE 自测。只有所有验证通过才能发布正式 Release。

## 使用流程

1. 打开工具，确认本地只读采集。
2. 选择固定驱动器，**在扫描前选择数据采集范围**。没有选择文件系统元数据时，不会全盘遍历文件。
3. 等待扫描结束，在 Review 中检查硬件、驱动器和可选清单，并逐项选择要导出的内容。
4. 确认最终类别和数量，选择 ZIP 目录；程序在后台生成并验证后，才发布最终文件。
5. 手动打开 `PC_Context_Pack_YYYYMMDD_HHMMSS.zip` 检查内容，再决定是否提供给 AI。

## ZIP 内容和稳定 Schema

根目录为 `PC_Context_Pack/`：

| 文件 | 条件 |
|---|---|
| `00_README_FOR_AI.md` | 始终包含，固定且不插入动态机器数据 |
| `01_PC_PROFILE/system_profile.json` | 选择系统概况 |
| `02_SOFTWARE/installed_software.csv` | 扫描前授权软件采集，且 Review 中选中条目 |
| `03_STORAGE/volumes.csv` | 选择存储信息，卷标脱敏 |
| `04_FILE_INDEX/files.csv` 和 `folders.csv` | 扫描前授权文件元数据采集，且 Review 选中相应条目 |
| `05_SECURITY/excluded_items_summary.csv` | 选择排除统计 |
| `06_SCAN_REPORT/scan_report.json`、`manifest.json` | 始终包含 |
| `06_SCAN_REPORT/warnings.csv` | 选择导出经过脱敏的错误代码 |

`manifest.json` 提供 `schema_version: "2.0"`、`application_version`、`collection_scope`、`selected_categories` 和实际记录数。文件系统状态 `not_collected` 表示采集前主动关闭索引，并不等于扫描失败。其他状态包括 `completed`、`partial_errors` 和 `partial_limit`。

[Schema v2.0 与信任边界说明](docs/SCHEMA_V2.md)。

## 隐私与限制

- 隐藏/系统目录、重解析点、常见云同步目录和凭据候选目录会尽力排除，但此类识别是启发式的，不承诺覆盖所有自定义路径。
- 用户选择导出文件名、软件名时，它们仍可能包含私人信息。**没有自动上传，不代表分享后的 ZIP 不会泄密。**
- ZIP 临时文件在生成期间存在于本地输出目录；正常失败会清理。极端断电或文件系统损坏可能留下无法确认身份的残留，程序不会冒险清除。
- 多个目录之间没有原子事务；这里的“原子发布”指仅在本地 ZIP 完整校验成功后才赋予最终文件名，而非跨磁盘断电级事务保证。
- Windows CI 不等于用户设备上的真实 GUI 操作验证。请单独确认目标电脑的运行体验。
- 本工具主要用于向 AI 提供环境信息，不是杀毒工具、完整系统审计工具或密码管理器。

## 开发者验证

```powershell
python -m compileall -q main.py privacy_policy.py context_schema.py staging_recovery.py tests benchmarks
python -m unittest discover -s tests -v
python main.py --self-test
python benchmarks/synthetic_perf.py --files 4000 --report perf.json
```

发布版在 GitHub Actions 中额外执行冻结后的 EXE 自检、文件清单验证、SHA-256 和发布资产完整性检查。运行历史见 [Actions](https://github.com/amor-purus/PC-Context-Builder/actions)。

## 安全、许可与历史

请勿将真实 PC Context Pack、私人路径、敏感截图、日志或凭据提交到 GitHub Issue 或代码仓库；参见 [SECURITY.md](SECURITY.md)。项目使用 [MIT License](LICENSE)。

既往 v1.0.9/v1.0.8 的历史验证说明仍保存在 [VERIFICATION_STATUS.txt](VERIFICATION_STATUS.txt) 中，但不应视为 v2.0.0 的实机验收证据。
