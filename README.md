# PC Context Builder v1.0.9

**Your PC. Understood by AI.**

PC Context Builder 是一个面向 Windows 11 的本地电脑环境采集与上下文构建工具。它将硬件、系统、软件以及用户选择的文件/文件夹元数据整理为 AI 助手可理解的上下文资料包。采集结果会先展示给用户审核；只有经过明确选择和最终确认后，才会生成 ZIP。

> **隐私原则：** 所有采集与打包都在本机完成，不会自动上传扫描结果；不读取文档正文、图片像素或视频/音频内容。软件清单、文件夹和文件元数据默认不纳入输出。生成的真实 PC Context Pack 可能包含设备标识等敏感元数据，分享前必须检查。

## 功能

- **本地只读采集**：Windows 系统、硬件、CPU、内存、GPU、显示器、固定驱动器等信息。
- **可选元数据索引**：软件清单、文件夹路径、文件名、大小和修改时间；这些类别默认不纳入 ZIP。
- **审核后导出**：在 GUI 中检查扫描结果，逐项选择输出类别，再生成 ZIP。
- **AI 友好结构**：输出系统配置、存储、可选软件与文件索引、扫描报告和隐私说明。
- **隐私保护**：敏感目录、凭据候选、常见云同步目录排除；CSV 文本字段进行公式注入防护。

## 环境要求

- Windows 11 x64
- CPython 3.14 x64（默认安装路径：`%LOCALAPPDATA%\\Programs\\Python\\Python314\\python.exe`）
- 不需要第三方 pip 依赖
- 使用 Windows PowerShell / CIM 读取系统信息

## 运行

1. 解压项目源码到本地目录。
2. 双击 `check_tool.bat`，确认显示 `SELF-TEST PASS`。
3. 双击 `start.bat` 启动 PC Context Builder。
4. 选择需要扫描的本地固定驱动器。
5. 在审核页面检查各类别。软件、文件夹、文件明细默认不纳入 ZIP。
6. 只选择需要提供给 AI 的信息，并执行最终确认。
7. 生成的文件名为 `PC_Context_Pack_YYYYMMDD_HHMMSS.zip`。分享前检查 ZIP 内容；ZIP 本身不加密。

## 输出结构

ZIP 内部使用 `PC_Context_Pack/` 作为根目录，包含按类别组织的资料，例如：

- `00_README_FOR_AI.md`：采集边界、隐私说明和使用指引
- `01_PC_PROFILE/system_profile.json`：系统与硬件概要
- `02_SOFTWARE/installed_software.csv`：用户选择的软件清单
- `03_STORAGE/volumes.csv`：驱动器容量信息
- `04_FILE_INDEX/`：用户选择的文件和文件夹元数据
- `05_SECURITY/`：排除项摘要
- `06_SCAN_REPORT/`：扫描报告、警告与清单

## 安全边界

- 本工具进行本地只读采集，不修改源文件、注册表或 Windows 设置。
- 不自动联网传输扫描结果，不读取文件正文。
- 软件清单、文件夹和文件元数据由用户主动选择，默认排除。
- 敏感目录和云同步目录识别属于启发式防护，不能保证识别所有自定义位置。
- ZIP 未加密，可能包含硬件型号、操作系统信息、软件清单或其他机器元数据；分享前必须检查内容。
- 请勿将真实 PC Context Pack、扫描报告、截图、日志、凭据或个人文件清单提交到 GitHub。

## 测试

本地自检：

```powershell
& "$env:LOCALAPPDATA\\Programs\\Python\\Python314\\python.exe" .\\main.py --self-test
```

GitHub Actions 在 Windows runner 上执行语法编译和内置 self-test。CI 不能替代目标电脑上的实际 GUI、WMI/CIM 与驱动器扫描验证。

## 版本状态

- **最新正式发布版本：** v1.0.8（原产品名 AI PC Intelligence）
- **当前品牌更新：** v1.0.9 候选版本，尚未发布
- v1.0.8 纳入了 Phase 1 安全加固：CSV 公式注入防护、敏感目录多级路径匹配，以及常见云同步目录/同步根目录识别。
- v1.0.8 的 Windows 11 实机验证记录与 v1.0.7 历史扫描基线见 [VERIFICATION_STATUS.txt](VERIFICATION_STATUS.txt)。

v1.0.9 的改名范围包括应用名称、界面文字、导出 ZIP 文件名及内部目录名称。扫描和隐私过滤逻辑不在本次品牌更新范围内。已发布的 v1.0.8 标签和 Release 保持不变。

## 仓库内容范围

仓库只包含程序源代码、启动脚本、文档和自动化测试配置。Git 忽略规则同时排除新旧命名的本地 PC 资料包、日志、缓存和临时输出。

本仓库尚未附加软件许可证。公开仓库不等于自动授予自由使用、修改或再发布的权利；如需按开源方式分发，应由项目所有者明确选择许可证。
