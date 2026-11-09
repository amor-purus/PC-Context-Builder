# AI PC Intelligence v1.0.7

一个面向 Windows 11 的本地 PC 环境采集工具。它读取系统与硬件信息、软件注册信息，以及用户选择范围内的文件/文件夹**元数据**；先展示完整结果供用户审核，只有经过明确选择和最终确认后才生成 ChatGPT 可读取的 ZIP。

> **隐私原则：** 工具本身不会联网上传采集结果；不读取文档正文、图片像素、视频/音频内容；软件清单、文件名、路径默认不纳入输出。生成的真实 PC 知识包可能包含设备标识等敏感元数据，切勿提交到 GitHub。

## 环境要求

- Windows 11 x64
- CPython 3.14 x64（默认安装路径：`%LOCALAPPDATA%\\Programs\\Python\\Python314\\python.exe`）
- 不需要第三方 pip 依赖
- 使用 Windows PowerShell / CIM 读取系统信息

## 运行

1. 解压本仓库到本地目录。
2. 双击 `check_tool.bat`，确认 `SELF-TEST PASS`。
3. 双击 `start.bat` 启动 GUI。
4. 选择需要扫描的本地固定驱动器。
5. 在审核页面检查各类别。软件、文件夹、文件明细默认不纳入 ZIP。
6. 确认选择后，使用窗口底部的 ZIP 创建操作生成知识包。
7. 分享前检查 ZIP 内容；ZIP 本身不加密。

## 关键实现

- PowerShell 子进程通过 `communicate(timeout=...)` 同时排空 stdout/stderr，避免大体积 JSON 输出导致管道死锁。
- 内存通过 Windows `GlobalMemoryStatusEx` 作为 CIM 数据缺失时的补充来源。
- 读取主板信息与双显卡设备信息（取决于 WMI/CIM 提供程序）。
- 系统保护目录的预期权限拒绝按跳过处理；其他权限错误写入扫描报告。
- Android ADB `adbkey` / `adbkey.pub` 作为机敏候选，默认排除。
- GUI 子窗口使用非模态 Toplevel，避免 Windows transient/grab 组合的任务栏恢复问题；messagebox 显式绑定 parent。

## 测试

本地自检：

```powershell
& "$env:LOCALAPPDATA\\Programs\\Python\\Python314\\python.exe" .\\main.py --self-test
```

GitHub Actions 在 Windows runner 上执行语法编译和内置 self-test。CI 不能代替目标电脑上的实际 GUI、WMI/CIM 与驱动器扫描验证。

## 版本与验证状态

详见 [`CHANGELOG.txt`](CHANGELOG.txt) 和 [`VERIFICATION_STATUS.txt`](VERIFICATION_STATUS.txt)。v1.0.7 已通过代码级/合成测试，并在用户 Windows 11 实机完成 GUI 操作、硬件信息采集、真实驱动器扫描与 ZIP 生成。该次扫描有 3 条 C: `PermissionError`，状态为 `partial_errors`；详情见验证记录。

## 仓库内容范围

只提交程序源代码、启动脚本、文档和自动化测试配置。`.gitignore` 会排除本地生成的 `AI_PC_Knowledge_Pack_*.zip`、日志、缓存和临时输出。不要提交用户真实的 PC 知识包、截图、扫描报告或个人文件清单。

本仓库当前未附加软件许可证；如需开源发布，应先由项目所有者明确选择许可证。
