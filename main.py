# -*- coding: utf-8 -*-
"""PC Context Builder v1.1.0 - Local, read-only Windows PC context packager.

No third-party Python packages are required. File contents are never opened or copied.
"""
from __future__ import annotations

import argparse
import csv
import ctypes
import datetime as dt
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import zipfile
from ctypes import wintypes
from pathlib import Path
from tkinter import Tk, Toplevel, StringVar, BooleanVar, filedialog, messagebox
from tkinter import ttk

from app_config import APP_NAME
from i18n import (
    LANGUAGE_CODES_BY_NAME, LANGUAGE_NAMES, LANGUAGE_ORDER,
    load_language_preference, save_language_preference, tr, translate_widget_tree, ui_font,
)
VERSION = "1.1.0"
MAX_FILES = 150_000
MAX_FOLDERS = 30_000
MAX_SCAN_SECONDS = 600
FILE_PAGE_SIZE = 500
FOLDER_PAGE_SIZE = 250
SOFTWARE_PAGE_SIZE = 250

EXCLUDED_DIR_NAMES = {
    "windows", "windows.old", "$windows.~bt", "$windows.~ws", "$winreagent",
    "program files", "program files (x86)", "programdata",
    "onedrive", "dropbox", "google drive", "icloud drive", "sharepoint", "box sync", "box drive",
    "$recycle.bin", "system volume information", "recovery", "perflogs",
    "windowsapps", "msocache", "config.msi", "appdata", "application data",
    "local settings", "temporary internet files", "onedrivetemp",
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", "site-packages", "pip-cache",
}

# Common cloud-sync roots. The environment-variable paths cover renamed
# organization folders and custom sync locations where Windows exposes them.
CLOUD_SYNC_DIR_NAMES = {
    "onedrive", "dropbox", ".dropbox.cache", "google drive", "googledrivefs",
    "icloud drive", "box", "box sync", "box drive", "sharepoint",
    "my drive", "shared drives",
}
CLOUD_SYNC_ROOT_ENV_VARS = (
    "OneDrive", "OneDriveCommercial", "OneDriveConsumer", "Dropbox",
    "GOOGLE_DRIVE", "GoogleDrive", "ICLOUD_DRIVE", "BOX_DRIVE", "SharePoint",
)
SENSITIVE_DIR_NAMES = {
    ".ssh", ".gnupg", ".aws", ".azure", ".config/gcloud",
    "credentials", "credential", "secrets", "secret", "private_keys",
    "private keys", "passwords", "password vault", "wallets",
}
SENSITIVE_NAME_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in (
        r"(^|[._ -])\.env($|[._ -])", r"credential", r"secret", r"password",
        r"passwd", r"token", r"api[_ -]?key", r"access[_ -]?key",
        r"id_rsa", r"id_ed25519", r"private[_ -]?key", r"(^|[\\/])adbkey(?:\.pub)?($|[._ -])", r"\.pem$",
        r"\.pfx$", r"\.p12$", r"\.key$", r"\.kdbx$", r"keepass",
        r"wallet", r"auth[_ -]?info", r"cookies?", r"session",
        r"personal", r"private", r"confidential", r"medical", r"health",
        r"finance", r"bank", r"tax", r"passport", r"identity", r"id[_ -]?card", r"ssn",
    )
]

PS_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = (New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $false)
function Safe-Text($v) { if ($null -eq $v) { return '' } return [string]$v }
$cimWarnings = New-Object System.Collections.Generic.List[string]
function Get-CimSafe([string]$ClassName) {
  try {
    return @(Get-CimInstance -ClassName $ClassName -OperationTimeoutSec 8 -ErrorAction Stop)
  } catch {
    [void]$script:cimWarnings.Add(($ClassName + ': ' + $_.Exception.Message))
    return @()
  }
}
$osItems = @(Get-CimSafe 'Win32_OperatingSystem')
$csItems = @(Get-CimSafe 'Win32_ComputerSystem')
$cpuItems = @(Get-CimSafe 'Win32_Processor')
$gpuItems = @(Get-CimSafe 'Win32_VideoController')
$boardItems = @(Get-CimSafe 'Win32_BaseBoard')
$os = $osItems | Select-Object -First 1 | Select-Object Caption, Version, BuildNumber, OSArchitecture, WindowsDirectory
$cs = $csItems | Select-Object -First 1 | Select-Object Manufacturer, Model, TotalPhysicalMemory, SystemType
$cpu = @($cpuItems | ForEach-Object { [PSCustomObject]@{ Name=$_.Name; Manufacturer=$_.Manufacturer; Cores=$_.NumberOfCores; LogicalProcessors=$_.NumberOfLogicalProcessors } })
$gpu = @($gpuItems | ForEach-Object { [PSCustomObject]@{ Name=$_.Name; DriverVersion=$_.DriverVersion } })
$board = $boardItems | Select-Object -First 1 | Select-Object Manufacturer, Product, Version
$uninstallPaths = @(
 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
$apps = @()
foreach ($p in $uninstallPaths) {
  try {
    $apps += Get-ItemProperty -Path $p -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -and $_.SystemComponent -ne 1 -and $_.ReleaseType -notin @('Update','Hotfix','Security Update') } | ForEach-Object {
      $loc = Safe-Text $_.InstallLocation
      if ($env:USERPROFILE -and $loc.StartsWith($env:USERPROFILE, [System.StringComparison]::OrdinalIgnoreCase)) { $loc = '%USERPROFILE%' + $loc.Substring($env:USERPROFILE.Length) }
      $loc = [regex]::Replace($loc, '(?i)^[A-Z]:\\Users\\[^\\]+', '%USERPROFILE%')
      [PSCustomObject]@{ Name=(Safe-Text $_.DisplayName); Version=(Safe-Text $_.DisplayVersion); Publisher=(Safe-Text $_.Publisher); InstallLocation=$loc }
    }
  } catch { [void]$script:cimWarnings.Add(('Software registry read: ' + $_.Exception.Message)) }
}
$apps = @($apps | Sort-Object Name,Version,Publisher -Unique)
$out = [PSCustomObject]@{ OS=$os; Computer=$cs; CPU=$cpu; GPU=$gpu; BaseBoard=$board; Software=$apps; Warnings=@($cimWarnings.ToArray()) }
$out | ConvertTo-Json -Depth 6 -Compress
'''


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def is_windows() -> bool:
    return os.name == "nt"


def _communicate_with_timeout(proc, timeout: float, cancel_event=None, poll_interval: float = 0.20):
    """Drain stdout and stderr while waiting, preventing anonymous-pipe deadlocks.

    Popen.communicate(timeout=...) actively consumes both pipes. Retrying it after
    TimeoutExpired is supported by Python and preserves output collected so far.
    """
    deadline = time.monotonic() + max(0.1, float(timeout))
    while True:
        if cancel_event is not None and cancel_event.is_set():
            try:
                if proc.poll() is None:
                    proc.terminate()
            except (OSError, ProcessLookupError):
                pass
            try:
                proc.communicate(timeout=2.0)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except (OSError, ProcessLookupError):
                    pass
                try:
                    proc.communicate(timeout=3.0)
                except subprocess.TimeoutExpired:
                    # The process is killed; a final wait prevents a zombie where supported.
                    try:
                        proc.wait(timeout=1.0)
                    except Exception:
                        pass
            raise InterruptedError("ユーザーがスキャンを停止しました。")

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            try:
                if proc.poll() is None:
                    proc.kill()
            except (OSError, ProcessLookupError):
                pass
            try:
                proc.communicate(timeout=3.0)
            except subprocess.TimeoutExpired:
                try:
                    proc.wait(timeout=1.0)
                except Exception:
                    pass
            raise TimeoutError(f"PowerShellの情報取得が{timeout}秒でタイムアウトしました。")

        try:
            return proc.communicate(timeout=min(poll_interval, remaining))
        except subprocess.TimeoutExpired:
            # communicate() is still draining both stdout and stderr in the
            # background; the next call only waits/checks cancellation again.
            continue


def run_powershell_json(script: str, timeout: int = 60, cancel_event=None):
    if not is_windows():
        raise RuntimeError("この機能はWindows上で実行してください。")
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    ps_candidates = [
        os.path.join(system_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"),
        os.path.join(system_root, "Sysnative", "WindowsPowerShell", "v1.0", "powershell.exe"),
    ]
    ps = next((p for p in ps_candidates if os.path.isfile(p)), None)
    if not ps:
        raise RuntimeError("Windows PowerShell が見つかりません。")
    import base64
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    proc = subprocess.Popen(
        [ps, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    stdout, stderr = _communicate_with_timeout(proc, timeout=timeout, cancel_event=cancel_event)
    if proc.returncode != 0:
        raise RuntimeError((stderr or stdout or "PowerShell CIM取得に失敗しました。")[-3000:])
    out = (stdout or "").strip().lstrip("\ufeff")
    if not out:
        raise RuntimeError("PowerShellから空の結果が返されました。")
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        sample = out[-1000:]
        raise RuntimeError(f"PowerShell JSON解析に失敗しました: {exc}. 出力末尾: {sample}") from exc


def format_bytes(value):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return ""
    if n < 0:
        return ""
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    for unit in units:
        if n < 1024 or unit == units[-1]:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return ""


def mask_path(path: str) -> str:
    if not path:
        return ""
    value = os.path.normpath(str(path))
    profile = os.environ.get("USERPROFILE", "")
    if profile:
        try:
            if os.path.commonpath([os.path.normcase(value), os.path.normcase(profile)]) == os.path.normcase(profile):
                rel = os.path.relpath(value, profile)
                return "%USERPROFILE%" if rel == "." else os.path.join("%USERPROFILE%", rel)
        except (ValueError, OSError):
            pass
    # Mask account directory names in standard Windows user-profile roots.
    value = re.sub(r"(?i)^[A-Z]:\\Users\\[^\\]+", r"%USERPROFILE%", value)
    return value


def is_sensitive_name(name: str, full_path: str = "") -> bool:
    text = f"{name} {full_path}"
    return any(p.search(text) for p in SENSITIVE_NAME_PATTERNS)


def is_sensitive_dir(name: str, full_path: str = "") -> bool:
    """Match sensitive directory names and multi-component paths.

    SENSITIVE_DIR_NAMES may contain either a leaf name (for example, ".ssh")
    or a relative path (for example, ".config/gcloud"). Matching path
    components avoids treating a partial name such as "gcloudish" as a match.
    """
    path_parts = [part.casefold() for part in re.split(r"[\\/]+", str(full_path or name)) if part]
    for candidate in SENSITIVE_DIR_NAMES:
        candidate_parts = [part.casefold() for part in re.split(r"[\\/]+", str(candidate).strip("/\\ ")) if part]
        if not candidate_parts:
            continue
        width = len(candidate_parts)
        if any(path_parts[index:index + width] == candidate_parts for index in range(len(path_parts) - width + 1)):
            return True
    return False


def is_cloud_sync_directory(name: str, full_path: str = "") -> bool:
    """Detect common sync-folder names and paths exposed by Windows clients."""
    low_name = str(name or "").casefold().strip()
    if low_name in CLOUD_SYNC_DIR_NAMES or low_name.startswith("onedrive - "):
        return True
    if not full_path:
        return False
    try:
        candidate_path = os.path.normcase(os.path.abspath(os.path.expandvars(str(full_path))))
    except (OSError, ValueError):
        return False
    for env_name in CLOUD_SYNC_ROOT_ENV_VARS:
        sync_root = os.environ.get(env_name)
        if not sync_root:
            continue
        try:
            root_path = os.path.normcase(os.path.abspath(os.path.expandvars(sync_root)))
            if os.path.commonpath((candidate_path, root_path)) == root_path:
                return True
        except (OSError, ValueError):
            continue
    return False


def get_display_resolution():
    """Return current desktop resolutions for displays attached to the desktop."""
    if not is_windows():
        return []
    try:
        class DISPLAY_DEVICE(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("DeviceName", ctypes.c_wchar * 32),
                ("DeviceString", ctypes.c_wchar * 128),
                ("StateFlags", ctypes.c_ulong),
                ("DeviceID", ctypes.c_wchar * 128),
                ("DeviceKey", ctypes.c_wchar * 128),
            ]

        class DEVMODE(ctypes.Structure):
            _fields_ = [
                ("dmDeviceName", ctypes.c_wchar * 32), ("dmSpecVersion", ctypes.c_ushort),
                ("dmDriverVersion", ctypes.c_ushort), ("dmSize", ctypes.c_ushort),
                ("dmDriverExtra", ctypes.c_ushort), ("dmFields", ctypes.c_ulong),
                ("dmOrientation", ctypes.c_short), ("dmPaperSize", ctypes.c_short),
                ("dmPaperLength", ctypes.c_short), ("dmPaperWidth", ctypes.c_short),
                ("dmScale", ctypes.c_short), ("dmCopies", ctypes.c_short),
                ("dmDefaultSource", ctypes.c_short), ("dmPrintQuality", ctypes.c_short),
                ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short),
                ("dmYResolution", ctypes.c_short), ("dmTTOption", ctypes.c_short),
                ("dmCollate", ctypes.c_short), ("dmFormName", ctypes.c_wchar * 32),
                ("dmLogPixels", ctypes.c_ushort), ("dmBitsPerPel", ctypes.c_ulong),
                ("dmPelsWidth", ctypes.c_ulong), ("dmPelsHeight", ctypes.c_ulong),
                ("dmDisplayFlags", ctypes.c_ulong), ("dmDisplayFrequency", ctypes.c_ulong),
                ("dmICMMethod", ctypes.c_ulong), ("dmICMIntent", ctypes.c_ulong),
                ("dmMediaType", ctypes.c_ulong), ("dmDitherType", ctypes.c_ulong),
                ("dmReserved1", ctypes.c_ulong), ("dmReserved2", ctypes.c_ulong),
                ("dmPanningWidth", ctypes.c_ulong), ("dmPanningHeight", ctypes.c_ulong)
            ]
        user32 = ctypes.windll.user32
        result = []
        index = 0
        while True:
            device = DISPLAY_DEVICE()
            device.cb = ctypes.sizeof(DISPLAY_DEVICE)
            if not user32.EnumDisplayDevicesW(None, index, ctypes.byref(device), 0):
                break
            index += 1
            if not (device.StateFlags & 0x1):  # DISPLAY_DEVICE_ATTACHED_TO_DESKTOP
                continue
            dm = DEVMODE()
            dm.dmSize = ctypes.sizeof(DEVMODE)
            if user32.EnumDisplaySettingsW(device.DeviceName, -1, ctypes.byref(dm)):
                result.append(f"{dm.dmPelsWidth} × {dm.dmPelsHeight}")
        return sorted(set(result))
    except Exception:
        return []


def get_python_environments():
    """Read registered Python installation metadata without executing discovered binaries."""
    result = []
    seen = set()
    current = os.path.abspath(sys.executable)
    try:
        bits = str(8 * __import__("struct").calcsize("P")) + "-bit"
        if current.lower().endswith(("python.exe", "pythonw.exe")):
            result.append({
                "Version": f"Python {platform.python_version()} (running)",
                "Path": mask_path(current),
                "Architecture": bits,
            })
            seen.add(os.path.normcase(current))
    except Exception:
        pass
    if not is_windows():
        return result
    try:
        import winreg
        roots = [
            (winreg.HKEY_CURRENT_USER, r"Software\Python\PythonCore", 0),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Python\PythonCore", winreg.KEY_WOW64_64KEY),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Python\PythonCore", winreg.KEY_WOW64_32KEY),
        ]
        for hive, base, view_flag in roots:
            try:
                with winreg.OpenKey(hive, base, 0, winreg.KEY_READ | view_flag) as root_key:
                    count = winreg.QueryInfoKey(root_key)[0]
                    for index in range(count):
                        try:
                            version_key = winreg.EnumKey(root_key, index)
                            install_key_path = base + "\\" + version_key + r"\InstallPath"
                            with winreg.OpenKey(hive, install_key_path, 0, winreg.KEY_READ | view_flag) as install_key:
                                install_dir = winreg.QueryValueEx(install_key, "")[0]
                            if not install_dir:
                                continue
                            exe = os.path.abspath(os.path.join(str(install_dir), "python.exe"))
                            norm = os.path.normcase(exe)
                            if norm in seen or not os.path.isfile(exe):
                                continue
                            seen.add(norm)
                            arch = "32-bit (registry view)" if view_flag == winreg.KEY_WOW64_32KEY or version_key.endswith("-32") else "64-bit/不明"
                            result.append({"Version": f"Python {version_key}", "Path": mask_path(exe), "Architecture": arch})
                        except (OSError, ValueError):
                            continue
            except OSError:
                continue
    except Exception:
        pass
    return sorted(result, key=lambda x: (x.get("Version", "").casefold(), x.get("Path", "").casefold()))


def get_drive_metadata(roots):
    result = []
    for root in roots:
        drive = str(root).strip().rstrip("\\")
        if not re.match(r"^[A-Za-z]:$", drive) or not os.path.isdir(drive + "\\"):
            continue
        try:
            usage = shutil.disk_usage(drive + "\\")
            result.append({"Drive": drive, "VolumeName": "", "FileSystem": "",
                           "SizeBytes": usage.total, "FreeBytes": usage.free})
        except OSError:
            result.append({"Drive": drive, "VolumeName": "", "FileSystem": "",
                           "SizeBytes": None, "FreeBytes": None})
    return result


def get_physical_memory_bytes():
    """Read installed physical RAM via the Windows GlobalMemoryStatusEx API."""
    if not is_windows():
        return None

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        function = kernel32.GlobalMemoryStatusEx
        function.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
        function.restype = wintypes.BOOL
        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(status)
        if not function(ctypes.byref(status)):
            return None
        total = int(status.ullTotalPhys)
        return total if total > 0 else None
    except Exception:
        return None


def get_python_fallback_system(roots):
    win_version = platform.win32_ver()
    return {
        "OS": {"Caption": "Windows", "Version": platform.version(), "BuildNumber": win_version[1] or "",
               "OSArchitecture": platform.machine(), "WindowsDirectory": os.environ.get("SystemRoot", "")},
        "Computer": {"Manufacturer": "", "Model": "", "TotalPhysicalMemory": get_physical_memory_bytes(), "SystemType": platform.machine()},
        "CPU": ([{"Name": platform.processor() or "", "Manufacturer": "", "Cores": None,
                  "LogicalProcessors": os.cpu_count()}] if platform.processor() or os.cpu_count() else []),
        "GPU": [], "BaseBoard": {}, "Drives": get_drive_metadata(roots), "Software": [], "Warnings": [],
    }


def normalize_system_result(raw):
    os_info = raw.get("OS") or {}
    computer = raw.get("Computer") or {}
    cpu = raw.get("CPU") or []
    gpu = raw.get("GPU") or []
    baseboard = raw.get("BaseBoard") or {}
    drives = raw.get("Drives") or []
    software = raw.get("Software") or []
    if isinstance(cpu, dict): cpu = [cpu]
    if isinstance(gpu, dict): gpu = [gpu]
    if isinstance(baseboard, list): baseboard = baseboard[0] if baseboard else {}
    if not isinstance(baseboard, dict): baseboard = {}
    if isinstance(drives, dict): drives = [drives]
    if isinstance(software, dict): software = [software]
    memory = computer.get("TotalPhysicalMemory")
    try:
        memory_bytes = int(memory) if memory not in (None, "") else None
        if memory_bytes is not None and memory_bytes <= 0:
            memory_bytes = None
    except (TypeError, ValueError, OverflowError):
        memory_bytes = None
    if memory_bytes is None:
        memory_bytes = get_physical_memory_bytes()
    browser_summary = []
    for app in software:
        app_name = str(app.get("Name", ""))
        if re.search(r"(?i)(google chrome|microsoft edge|mozilla firefox|brave|opera|vivaldi)", app_name):
            browser_summary.append({"Name": app_name, "Version": app.get("Version", ""), "Publisher": app.get("Publisher", "")})
    for app in software:
        # Application names and publisher fields can reveal personal information.
        # Require explicit row selection in the review window.
        app["Include"] = False
    return {
        "collected_at": now_iso(),
        "computer_label": "LOCAL_PC (computer name masked)",
        "os": {
            "name": os_info.get("Caption", ""),
            "version": os_info.get("Version", ""),
            "build": os_info.get("BuildNumber", ""),
            "architecture": os_info.get("OSArchitecture", ""),
        },
        "hardware": {
            "manufacturer": computer.get("Manufacturer", ""),
            "model": computer.get("Model", ""),
            "system_type": computer.get("SystemType", ""),
            "cpu": cpu,
            "physical_memory_bytes": memory_bytes,
            "physical_memory_display": format_bytes(memory_bytes),
            "gpu": gpu,
            "motherboard_manufacturer": baseboard.get("Manufacturer", ""),
            "motherboard_product": baseboard.get("Product", ""),
            "motherboard_version": baseboard.get("Version", ""),
            "display_resolutions": get_display_resolution(),
        },
        "drives": drives,
        "software": software,
        "python_environments": get_python_environments(),
        "browser_summary": browser_summary,
    }


def get_fixed_drives(system_data):
    roots = []
    for d in system_data.get("drives", []):
        drive = str(d.get("Drive", "")).strip()
        if re.match(r"^[A-Za-z]:$", drive):
            root = drive + "\\"
            if os.path.isdir(root):
                roots.append(root)
    return sorted(set(roots))


def should_skip_dir(name: str, attrs: int, full_path: str):
    low = name.casefold()
    if low in {x.casefold() for x in EXCLUDED_DIR_NAMES}:
        return True, "protected_or_high_volume_directory"
    if is_sensitive_dir(name, full_path) or is_sensitive_name(name, full_path):
        return True, "sensitive_directory_candidate"
    if is_cloud_sync_directory(name, full_path):
        return True, "cloud_sync_directory"
    # Windows reparse point flag (junctions/symlinks/mount points).
    if attrs & 0x400:
        return True, "reparse_point_not_followed"
    # Do not traverse hidden/system directories in the inventory.
    if attrs & (0x2 | 0x4):
        return True, "hidden_or_system_directory"
    return False, ""


def should_skip_file(name: str, attrs: int, full_path: str):
    """Skip links and hidden/system files without reading their contents."""
    if attrs & 0x400:
        return True, "reparse_point_not_followed"
    if attrs & (0x2 | 0x4):
        return True, "hidden_or_system_file"
    if is_sensitive_name(name, full_path):
        return False, "sensitive_file_name_candidate"
    return False, ""


def display_path_for_drive(full_path: str, drive_root: str) -> str:
    """Return a drive-relative path with user profile directory names masked."""
    try:
        rel = os.path.relpath(full_path, drive_root)
    except (ValueError, OSError):
        return mask_path(full_path)
    profile = os.environ.get("USERPROFILE", "")
    if profile:
        try:
            if os.path.commonpath([os.path.normcase(full_path), os.path.normcase(profile)]) == os.path.normcase(profile):
                tail = os.path.relpath(full_path, profile)
                return "%USERPROFILE%" if tail == "." else os.path.join("%USERPROFILE%", tail)
        except (ValueError, OSError):
            pass
    rel = re.sub(r"(?i)^Users\\[^\\]+", r"%USERPROFILE%", rel)
    return rel


PROTECTED_ACCESS_DIR_NAMES = {
    "$recycle.bin", "system volume information", "windowsapps", "recovery",
    "windows", "windows.old", "program files", "program files (x86)",
    "programdata", "config.msi", "$windows.~bt", "$windows.~ws", "$winreagent",
}


def is_expected_protected_directory_path(path: str) -> bool:
    """Whether a path is inside a directory intentionally excluded from scanning."""
    normalized = str(path or "").replace("/", "\\")
    components = [part.casefold() for part in normalized.split("\\") if part]
    protected = {name.casefold() for name in PROTECTED_ACCESS_DIR_NAMES}
    return any(part in protected for part in components)


def record_expected_protected_skip(path: str, skipped_count: int, exclusions: list):
    skipped_count += 1
    if len(exclusions) < 5000:
        exclusions.append({"Category": "folder", "Reason": "expected_protected_directory_access_denied"})
    return skipped_count


def scan_filesystem(roots, q: queue.Queue, cancel_event: threading.Event):
    files, folders, warnings, exclusions = [], [], [], []
    started = time.monotonic()
    files_count = folders_count = skipped_count = error_count = 0
    limited = False
    for root in roots:
        if cancel_event.is_set():
            break
        stack = [(root, 0)]
        while stack:
            if cancel_event.is_set():
                break
            if time.monotonic() - started > MAX_SCAN_SECONDS or files_count >= MAX_FILES or folders_count >= MAX_FOLDERS:
                limited = True
                stack.clear()
                break
            current, depth = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if cancel_event.is_set():
                            break
                        if time.monotonic() - started > MAX_SCAN_SECONDS or files_count >= MAX_FILES or folders_count >= MAX_FOLDERS:
                            limited = True
                            break
                        try:
                            st = entry.stat(follow_symlinks=False)
                            attrs = getattr(st, "st_file_attributes", 0)
                            full = entry.path
                            if entry.is_symlink() or attrs & 0x400:
                                skipped_count += 1
                                if len(exclusions) < 5000:
                                    exclusions.append({"Category": "folder_or_file", "Reason": "reparse_point_not_followed"})
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                skip, reason = should_skip_dir(entry.name, attrs, full)
                                if skip:
                                    skipped_count += 1
                                    if len(exclusions) < 5000:
                                        exclusions.append({"Category": "folder", "Reason": reason})
                                    continue
                                folders.append({
                                    "Drive": root[:2], "Path": display_path_for_drive(full, root), "Depth": depth,
                                    "Include": False,
                                })
                                folders_count += 1
                                stack.append((full, depth + 1))
                            elif entry.is_file(follow_symlinks=False):
                                skip_file, file_reason = should_skip_file(entry.name, attrs, full)
                                if skip_file:
                                    skipped_count += 1
                                    if file_reason == "hidden_or_system_file" and len(exclusions) < 5000:
                                        exclusions.append({"Category": "file", "Reason": file_reason})
                                    continue
                                sensitive = file_reason == "sensitive_file_name_candidate"
                                if sensitive and len(exclusions) < 5000:
                                    exclusions.append({"Category": "file", "Reason": "sensitive_file_name_candidate"})
                                files.append({
                                    "Drive": root[:2], "Path": display_path_for_drive(full, root), "Name": entry.name,
                                    "Extension": os.path.splitext(entry.name)[1].lower(),
                                    "SizeBytes": int(st.st_size),
                                    "Modified": dt.datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds"),
                                    "PrivacyCandidate": "Yes" if sensitive else "No",
                                    # Default-deny for every file; users must explicitly opt in.
                                    "Include": False,
                                })
                                files_count += 1
                        except (PermissionError, OSError) as exc:
                            if isinstance(exc, PermissionError) and is_expected_protected_directory_path(entry.path):
                                skipped_count = record_expected_protected_skip(entry.path, skipped_count, exclusions)
                            else:
                                error_count += 1
                                if len(warnings) < 5000:
                                    warnings.append({"Drive": (entry.path[:2] if re.match(r"^[A-Za-z]:", entry.path) else "local"), "Reason": f"metadata_error: {type(exc).__name__}"})
                        processed = files_count + folders_count
                        if processed and processed % 500 == 0:
                            q.put(("progress", {"files": files_count, "folders": folders_count, "skipped": skipped_count, "errors": error_count, "current": mask_path(current)}))
                if limited:
                    stack.clear()
                    break
            except (PermissionError, OSError) as exc:
                if isinstance(exc, PermissionError) and is_expected_protected_directory_path(current):
                    skipped_count = record_expected_protected_skip(current, skipped_count, exclusions)
                else:
                    error_count += 1
                    if len(warnings) < 5000:
                        warnings.append({"Drive": (current[:2] if re.match(r"^[A-Za-z]:", current) else "local"), "Reason": f"access_error: {type(exc).__name__}"})
        if limited:
            break
    files.sort(key=lambda r: (r["Drive"], r["Path"].casefold(), r["Name"].casefold()))
    folders.sort(key=lambda r: (r["Drive"], r["Path"].casefold()))
    if cancel_event.is_set():
        status = "cancelled"
    elif limited:
        status = "partial_limit"
    elif error_count:
        status = "partial_errors"
    else:
        status = "completed"
    q.put(("filesystem_done", {
        "files": files, "folders": folders, "warnings": warnings, "exclusions": exclusions,
        "counts": {"files": len(files), "folders": len(folders), "skipped": skipped_count, "errors": error_count},
        "status": status,
        "elapsed_seconds": round(time.monotonic() - started, 1),
    }))


def create_scan_payload(q: queue.Queue, cancel_event: threading.Event, selected_roots):
    warnings = []
    q.put(("status", "システム構成を取得しています..."))
    selected_roots = [str(x).strip().rstrip("\\") + "\\" for x in selected_roots if str(x).strip()]
    try:
        raw = run_powershell_json(PS_SCRIPT, timeout=50, cancel_event=cancel_event)
        if isinstance(raw, dict):
            for item in raw.get("Warnings", []) or []:
                warnings.append({"Drive": "system", "Reason": "CIM_unavailable: " + str(item)[:500]})
    except InterruptedError:
        raise
    except Exception as exc:
        raw = get_python_fallback_system(selected_roots)
        warnings.append({"Drive": "system", "Reason": f"PowerShell_CIM_unavailable_python_fallback_used: {type(exc).__name__}: {str(exc)[:300]}"})
    system = normalize_system_result(raw)
    q.put(("status", "ローカル固定ドライブを確認しています..."))
    roots = [r for r in selected_roots if os.path.isdir(r)]
    system["drives"] = get_drive_metadata(roots)
    if not roots:
        warnings.append({"Drive": "local", "Reason": "selected_drives_unavailable_or_not_fixed"})
        fs_result = {
            "files": [], "folders": [], "warnings": [], "exclusions": [],
            "counts": {"files": 0, "folders": 0, "skipped": 0, "errors": 1},
            "status": "partial_errors", "elapsed_seconds": 0.0,
        }
    else:
        q.put(("status", f"ファイル構造を調査しています（選択ドライブ {len(roots)} 個）..."))
        fsq = queue.Queue()
        fs_thread = threading.Thread(target=scan_filesystem, args=(roots, fsq, cancel_event), daemon=True)
        fs_thread.start()
        fs_result = None
        while fs_thread.is_alive() or not fsq.empty():
            try:
                kind, data = fsq.get(timeout=0.25)
            except queue.Empty:
                continue
            if kind == "progress":
                q.put(("progress", data))
            elif kind == "filesystem_done":
                fs_result = data
        fs_thread.join(timeout=1)
        if fs_result is None:
            raise RuntimeError("ファイル構造スキャンの結果を取得できませんでした。")
    if cancel_event.is_set() or fs_result.get("status") == "cancelled":
        q.put(("cancelled", None))
        return
    payload = {
        "scan_time": now_iso(),
        "system": system,
        "roots": roots,
        "files": fs_result["files"],
        "folders": fs_result["folders"],
        "warnings": fs_result["warnings"],
        "exclusions": fs_result["exclusions"],
        "filesystem_counts": fs_result["counts"],
        "filesystem_status": fs_result["status"],
        "filesystem_elapsed_seconds": fs_result["elapsed_seconds"],
        "scan_warnings": warnings,
    }
    q.put(("done", payload))


CSV_FORMULA_PREFIX_RE = re.compile(r"^[\s\x00-\x1f\ufeff\u200b\u200c\u200d]*[=+\-@]")


def sanitize_csv_cell(value):
    """Neutralize spreadsheet formula triggers in untrusted text fields.

    Numeric values remain numeric. Text beginning with a spreadsheet formula
    operator after whitespace/control characters is prefixed with an apostrophe
    so common spreadsheet applications treat it as text when opening the CSV.
    """
    if not isinstance(value, str):
        return value
    if value.startswith(("\t", "\r", "\n")) or CSV_FORMULA_PREFIX_RE.match(value):
        return "'" + value
    return value


def csv_bytes(rows, headers):
    import io
    buff = io.StringIO(newline="")
    writer = csv.DictWriter(buff, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: sanitize_csv_cell(value) for key, value in row.items()})
    return buff.getvalue().encode("utf-8-sig", errors="replace")


def safe_json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8-sig", errors="replace")


def generate_readme(payload, selected, included_counts, language="en"):
    sysd = payload["system"]
    hw = sysd.get("hardware", {})
    osd = sysd.get("os", {})
    lines = [
        "# PC Context Pack", "",
        f"- Schema version: {VERSION}",
        f"- Scan time: {payload.get('scan_time','')}",
        "- Collection method: local read-only inventory", 
        "- Network upload: not performed",
        "- File contents: NOT collected or copied",
        "- Machine and user path masking: applied where supported",
        "",
        "## PC overview", "",
    ]
    if selected.get("system"):
        lines += [
            f"- OS: {osd.get('name','')} {osd.get('version','')} (Build {osd.get('build','')})",
            f"- Architecture: {osd.get('architecture','')}",
            f"- Manufacturer / Model: {hw.get('manufacturer','')} / {hw.get('model','')}",
            f"- Motherboard: {hw.get('motherboard_manufacturer','')} / {hw.get('motherboard_product','')} / {hw.get('motherboard_version','')}",
            f"- CPU: {', '.join(x.get('Name','') for x in hw.get('cpu',[]) if x.get('Name'))}",
            f"- Physical memory: {hw.get('physical_memory_display','')}",
            f"- GPU: {', '.join(x.get('Name','') for x in hw.get('gpu',[]) if x.get('Name'))}",
            f"- Display: {', '.join(hw.get('display_resolutions',[]))}",
        ]
    else:
        lines.append("- PC profile was not selected for inclusion.")
    lines += ["", "## Included categories", "",
    ]
    labels = {"system": "PC profile", "software": "Installed software", "drives": "Storage", "folders": "Folder index", "files": "File metadata index", "warnings": "Scan warnings", "security": "Security/exclusion summary"}
    for key, label in labels.items():
        lines.append(f"- {label}: {'included' if selected.get(key) else 'not included'} ({included_counts.get(key,0)} records)")
    lines += [
        "", "## Privacy and interpretation", "",
        "This package contains inventory metadata only. It does not include document text, image pixels, video/audio contents, browser history, cookies, saved passwords, API keys, tokens, SSH private keys, or Windows credentials.",
        "File and folder names can still reveal personal information. Review this package before sharing it. Candidate sensitive names are excluded by default, but heuristic detection is not perfect.",
        "Paths under the current user profile are represented with %USERPROFILE% where detected. Some third-party software paths may still contain identifying details.",
        "System/application directories, common cloud-sync folders, hidden/system files and folders, reparse points, caches, and known credential folders were excluded from the file-system walk.",
        "Software names, folder paths, and file metadata are opt-in: their rows are excluded by default until individually selected in the review window.",
        "A partial scan or access errors mean the inventory is incomplete. See scan_report.json and warnings.csv.",
        "", "## How an AI assistant should use this package", "",
        "Use system_profile.json to understand the machine environment; installed_software.csv to identify selected software; volumes.csv for storage; folders.csv and files.csv as a searchable metadata index only. Do not assume the package contains file contents.",
    ]
    return "\n".join(tr(line, language) for line in lines) + "\n"


def build_package(payload, choices, output_dir, language="en"):
    selected = dict(choices.get("categories", {}))
    system = payload["system"]
    files = [r for r in payload["files"] if r.get("Include", False)] if selected.get("files") else []
    folders = [r for r in payload["folders"] if r.get("Include", False)] if selected.get("folders") else []
    software = [r for r in system.get("software", []) if r.get("Include", False)] if selected.get("software") else []
    drives = system.get("drives", []) if selected.get("drives") else []
    warnings = (payload.get("warnings", []) + payload.get("scan_warnings", [])) if selected.get("warnings") else []
    exclusions = payload.get("exclusions", []) if selected.get("security") else []
    system_out = json.loads(json.dumps(system, ensure_ascii=False)) if selected.get("system") else {}
    if system_out and selected.get("software"):
        included_apps = [r for r in system.get("software", []) if r.get("Include", False)]
        include_names = {str(r.get("Name", "")) for r in included_apps}
        system_out["software"] = [{k:v for k,v in r.items() if k != "Include"} for r in included_apps]
        system_out["browser_summary"] = [r for r in system_out.get("browser_summary", []) if r.get("Name") in include_names]
    elif system_out:
        system_out.pop("software", None)
        system_out.pop("browser_summary", None)
    if system_out and selected.get("drives"):
        system_out["drives"] = drives
    elif system_out:
        system_out.pop("drives", None)
    counts = {
        "system": 1 if system_out else 0,
        "software": len(software), "drives": len(drives),
        "folders": len(folders), "files": len(files),
        "warnings": len(warnings), "security": len(exclusions),
    }
    manifest = {
        "schema_version": VERSION,
        "ui_language": language,
        "generated_at": now_iso(),
        "scan_time": payload.get("scan_time"),
        "scan_status": payload.get("filesystem_status"),
        "selected_categories": selected,
        "record_counts": counts,
        "privacy": {"file_contents_collected": False, "network_upload_performed": False, "user_paths_masked_where_detected": True},
        "limits": {"max_files": MAX_FILES, "max_folders": MAX_FOLDERS, "max_scan_seconds": MAX_SCAN_SECONDS},
    }
    date_tag = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(output_dir, f"PC_Context_Pack_{date_tag}.zip")
    suffix = 2
    while os.path.exists(dest):
        dest = os.path.join(output_dir, f"PC_Context_Pack_{date_tag}_{suffix}.zip")
        suffix += 1
    temp = dest + ".tmp"
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            zf.writestr("PC_Context_Pack/00_README_FOR_AI.md", generate_readme(payload, selected, counts, language))
            if system_out:
                zf.writestr("PC_Context_Pack/01_PC_PROFILE/system_profile.json", safe_json_bytes(system_out))
            if selected.get("software"):
                zf.writestr("PC_Context_Pack/02_SOFTWARE/installed_software.csv", csv_bytes(software, ["Name","Version","Publisher","InstallLocation"]))
            if selected.get("drives"):
                zf.writestr("PC_Context_Pack/03_STORAGE/volumes.csv", csv_bytes(drives, ["Drive","VolumeName","FileSystem","SizeBytes","FreeBytes"]))
            if selected.get("folders"):
                zf.writestr("PC_Context_Pack/04_FILE_INDEX/folders.csv", csv_bytes(folders, ["Drive","Path","Depth"]))
            if selected.get("files"):
                zf.writestr("PC_Context_Pack/04_FILE_INDEX/files.csv", csv_bytes(files, ["Drive","Path","Name","Extension","SizeBytes","Modified","PrivacyCandidate"]))
            if selected.get("security"):
                zf.writestr("PC_Context_Pack/05_SECURITY/excluded_items_summary.csv", csv_bytes(exclusions, ["Category","Reason"]))
            if selected.get("warnings"):
                zf.writestr("PC_Context_Pack/06_SCAN_REPORT/warnings.csv", csv_bytes(warnings, ["Drive","Reason"]))
            zf.writestr("PC_Context_Pack/06_SCAN_REPORT/scan_report.json", safe_json_bytes({
                "scan_status": payload.get("filesystem_status"),
                "filesystem_counts": payload.get("filesystem_counts"),
                "elapsed_seconds": payload.get("filesystem_elapsed_seconds"),
                "warnings_count": len(payload.get("warnings", [])) + len(payload.get("scan_warnings", [])),
                "excluded_count": len(payload.get("exclusions", [])),
                "roots_scanned": payload.get("roots", []),
            }))
            zf.writestr("PC_Context_Pack/06_SCAN_REPORT/manifest.json", safe_json_bytes(manifest))
        with zipfile.ZipFile(temp, "r") as zf:
            bad = zf.testzip()
            if bad:
                raise RuntimeError(f"ZIP integrity check failed: {bad}")
        os.replace(temp, dest)
        return dest, counts, os.path.getsize(dest)
    except Exception:
        try:
            if os.path.exists(temp): os.remove(temp)
        except OSError:
            pass
        raise


class ReviewWindow(Toplevel):
    def __init__(self, master, payload, on_confirm, language="ja"):
        super().__init__(master)
        self.language = language
        self.title(tr("収集結果の確認と梱包対象の選択", self.language))
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(1080, max(760, screen_w - 60))
        height = min(720, max(520, screen_h - 90))
        self.geometry(f"{width}x{height}+{max(0,(screen_w-width)//2)}+{max(0,(screen_h-height)//2)}")
        self.minsize(760, 520)
        self.payload = payload
        self.on_confirm = on_confirm
        self.result = None
        self.categories = {
            "system": BooleanVar(value=True),
            "software": BooleanVar(value=False),
            "drives": BooleanVar(value=True),
            "folders": BooleanVar(value=False),
            "files": BooleanVar(value=False),
            "warnings": BooleanVar(value=True),
            "security": BooleanVar(value=True),
        }
        self.file_page_rows = []
        self.file_search_var = StringVar()
        self.file_page = 0
        self.folder_page = 0
        self.software_page = 0
        self.status_var = StringVar(value=tr("メタデータ一覧を確認してください。", self.language))
        self._on_close_callback = None
        self._closed = False
        self._build()
        # Do not use transient() or grab_set() on Windows. This review window
        # has an independent native-window lifecycle so taskbar activation is
        # not blocked by a child-window grab. App disables the scan button
        # while this review window is open to prevent duplicate scans.
        self.protocol("WM_DELETE_WINDOW", self._close_review)
        self.after(100, self._activate_window)

    def _activate_window(self):
        """Raise a newly-created review window after Windows has mapped it."""
        try:
            if self.winfo_exists():
                if self.state() == "iconic":
                    self.deiconify()
                self.lift()
                # This is called only after an explicit in-app action creates
                # the review window, not repeatedly while the user is elsewhere.
                self.focus_force()
        except Exception:
            pass

    def set_language(self, language):
        self.language = language
        self.title(tr("収集結果の確認と梱包対象の選択", self.language))
        self.status_var.set(tr("メタデータ一覧を確認してください。", self.language))
        self._build()

    def t(self, text):
        return tr(text, self.language)

    def set_on_close(self, callback):
        self._on_close_callback = callback

    def _close_review(self):
        if self._closed:
            return
        self._closed = True
        callback = self._on_close_callback
        try:
            self.destroy()
        finally:
            if callback:
                try:
                    callback(self)
                except Exception:
                    pass

    def _build(self):
        old_container = getattr(self, "container", None)
        if old_container is not None:
            try:
                old_container.destroy()
            except Exception:
                pass
        # Keep the action footer pinned to the bottom. The prior pack-only layout
        # allowed the expanding Notebook to consume the available height and clip
        # the footer (including the ZIP-creation action) on some Windows layouts.
        self.container = ttk.Frame(self)
        outer = self.container
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        top = ttk.Frame(outer, padding=12)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="スキャン結果のレビュー", font=ui_font(self.language, 16, "bold")).pack(anchor="w")
        counts = self.payload["filesystem_counts"]
        ttk.Label(top, text=f"ファイル {counts['files']:,} 件 / フォルダー {counts['folders']:,} 件 / 除外 {counts['skipped']:,} 件 / エラー {counts['errors']:,} 件", foreground="#555").pack(anchor="w", pady=(4,0))
        if self.payload.get("filesystem_status") != "completed":
            ttk.Label(top, text="注意：スキャンは部分完了です。ZIPのREADMEとscan_reportに未取得範囲が記録されます。", foreground="#b35b00", wraplength=980).pack(anchor="w", pady=(4,0))

        self.nb = ttk.Notebook(outer)
        self.nb.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        self._build_overview_tab()
        self._build_software_tab()
        self._build_drives_tab()
        self._build_files_tab()
        self._build_warnings_tab()

        bottom = ttk.Frame(outer, padding=12)
        bottom.grid(row=2, column=0, sticky="ew")
        ttk.Label(bottom, textvariable=self.status_var).pack(side="left", fill="x", expand=True)
        ttk.Button(bottom, text="閉じる（梱包しない）", command=self._close_review).pack(side="right", padx=5)
        ttk.Button(bottom, text="梱包内容を確認してZIP作成へ", command=self._approve).pack(side="right", padx=5)
        translate_widget_tree(self.container, self.language)

    def _tab(self, name):
        frame = ttk.Frame(self.nb, padding=10)
        self.nb.add(frame, text=name)
        return frame

    def _category_check(self, parent, key, label):
        ttk.Checkbutton(parent, text=label, variable=self.categories[key]).pack(anchor="w", pady=2)

    def _build_overview_tab(self):
        f = self._tab("PC概要")
        self._category_check(f, "system", "PC基本情報を梱包する")
        s = self.payload["system"]
        osd, hw = s.get("os", {}), s.get("hardware", {})
        lines = [
            ("OS", f"{osd.get('name','')} {osd.get('version','')} / Build {osd.get('build','')} / {osd.get('architecture','')}"),
            ("メーカー・モデル", f"{hw.get('manufacturer','')} / {hw.get('model','')}"),
            ("マザーボード", " / ".join(x for x in (hw.get("motherboard_manufacturer", ""), hw.get("motherboard_product", ""), hw.get("motherboard_version", "")) if x)),
            ("CPU", "; ".join(x.get("Name", "") for x in hw.get("cpu", []) if x.get("Name"))),
            ("メモリ", hw.get("physical_memory_display", "")),
            ("GPU", "; ".join(x.get("Name", "") for x in hw.get("gpu", []) if x.get("Name"))),
            ("ディスプレイ", "; ".join(hw.get("display_resolutions", []))),
            ("Python", "; ".join(x.get("Version", "") + " / " + x.get("Architecture", "") + " — " + x.get("Path", "") for x in s.get("python_environments", []))),
            ("ブラウザー", "; ".join(x.get("Name", "") + " " + x.get("Version", "") for x in s.get("browser_summary", []))),
        ]
        tree = ttk.Treeview(f, columns=("item","value"), show="headings", height=15)
        tree.heading("item", text=self.t("項目")); tree.heading("value", text=self.t("取得値"))
        tree.column("item", width=180, stretch=False); tree.column("value", width=750)
        for label, value in lines:
            tree.insert("", "end", values=(self.t(label), value))
        tree.pack(fill="both", expand=True, pady=8)
        ttk.Label(f, text="コンピューター名とユーザー名を含むパスは匿名化します。機器固有IDやシリアル番号は取得しません。", foreground="#555", wraplength=950).pack(anchor="w")

    def _build_software_tab(self):
        f = self._tab("ソフトウェア")
        apps = self.payload["system"].get("software", [])
        self._category_check(f, "software", f"インストール済みソフトウェア一覧を梱包する（{len(apps):,}件）")
        ttk.Label(f, text="アプリ名・発行元・バージョンを検索できます。初期状態ではすべて除外され、選択した行だけがZIPに入ります。", foreground="#555").pack(anchor="w", pady=4)
        search = ttk.Frame(f); search.pack(fill="x", pady=(0,5))
        if not hasattr(self, "software_search_var"):
            self.software_search_var = StringVar()
        ttk.Label(search, text="アプリ検索：").pack(side="left")
        ent = ttk.Entry(search, textvariable=self.software_search_var, width=36); ent.pack(side="left", padx=4)
        ent.bind("<KeyRelease>", lambda _e: self._reset_software_page())
        ttk.Button(search, text="表示ページをすべて含める", command=lambda: self._set_visible_software(True)).pack(side="left", padx=3)
        ttk.Button(search, text="表示ページをすべて除外", command=lambda: self._set_visible_software(False)).pack(side="left", padx=3)
        pager = ttk.Frame(f); pager.pack(fill="x", pady=(0,4))
        self.software_page_label = ttk.Label(pager, text="")
        self.software_page_label.pack(side="left")
        ttk.Button(pager, text="前へ", command=lambda: self._move_software_page(-1)).pack(side="right", padx=3)
        ttk.Button(pager, text="次へ", command=lambda: self._move_software_page(1)).pack(side="right", padx=3)
        self.software_tree = ttk.Treeview(f, columns=("include","name","version","publisher","location"), show="headings")
        cols = [("include","梱包",65,False),("name","アプリ名",260,True),("version","バージョン",120,False),("publisher","発行元",170,False),("location","インストール先（匿名化）",360,True)]
        for c,title,width,stretch in cols:
            self.software_tree.heading(c,text=title); self.software_tree.column(c,width=width,stretch=stretch)
        sw_table = ttk.Frame(f); sw_table.pack(fill="both", expand=True, pady=8)
        sw_scroll = ttk.Scrollbar(sw_table, orient="vertical", command=self.software_tree.yview)
        self.software_tree.configure(yscrollcommand=sw_scroll.set)
        self.software_tree.pack(side="left", fill="both", expand=True)
        sw_scroll.pack(side="right", fill="y")
        self.software_tree.bind("<Double-1>", self._toggle_software)
        self._refresh_software_tree()

    def _filtered_software_rows(self):
        query = self.software_search_var.get().strip().casefold()
        rows = self.payload["system"].get("software", [])
        if query:
            rows = [r for r in rows if query in str(r.get("Name","")).casefold()
                    or query in str(r.get("Publisher","")).casefold()
                    or query in str(r.get("Version","")).casefold()]
        return rows

    def _refresh_software_tree(self):
        if not hasattr(self, "software_tree"):
            return
        rows = self._filtered_software_rows()
        pages = max(1, (len(rows) + SOFTWARE_PAGE_SIZE - 1) // SOFTWARE_PAGE_SIZE)
        self.software_page = min(max(0, self.software_page), pages - 1)
        start = self.software_page * SOFTWARE_PAGE_SIZE
        self.software_rows = rows[start:start + SOFTWARE_PAGE_SIZE]
        self.software_tree.delete(*self.software_tree.get_children())
        for i, a in enumerate(self.software_rows):
            self.software_tree.insert("", "end", iid=str(i), values=(self.t("はい") if a.get("Include",False) else self.t("いいえ"),a.get("Name",""),a.get("Version",""),a.get("Publisher",""),a.get("InstallLocation","")))
        included = sum(1 for r in self.payload["system"].get("software", []) if r.get("Include",False))
        self.software_page_label.configure(text=self.t(f"検索結果 {len(rows):,} 件 / 全アプリ {len(self.payload['system'].get('software', [])):,} 件 / 選択 {included:,} 件 / ページ {self.software_page+1}/{pages}（1ページ {SOFTWARE_PAGE_SIZE} 件）"))

    def _reset_software_page(self):
        self.software_page = 0
        self._refresh_software_tree()

    def _move_software_page(self, delta):
        self.software_page += delta
        self._refresh_software_tree()

    def _set_visible_software(self, value):
        for row in self.software_rows:
            row["Include"] = value
        self._refresh_software_tree()

    def _toggle_software(self, event):
        item = self.software_tree.identify_row(event.y)
        if not item: return
        try:
            row = self.software_rows[int(item)]
            row["Include"] = not row.get("Include", False)
            vals = list(self.software_tree.item(item, "values"))
            vals[0] = self.t("はい") if row["Include"] else self.t("いいえ")
            self.software_tree.item(item, values=vals)
        except (IndexError, ValueError):
            return

    def _build_drives_tab(self):
        f = self._tab("ストレージ")
        drives = self.payload["system"].get("drives", [])
        self._category_check(f, "drives", f"ローカル固定ドライブ一覧を梱包する（{len(drives)}件）")
        tree = ttk.Treeview(f, columns=("drive","label","fs","size","free"), show="headings")
        for c, title, width in [("drive","ドライブ",100),("label","ボリューム名",200),("fs","ファイルシステム",160),("size","総容量",180),("free","空き容量",180)]:
            tree.heading(c,text=title); tree.column(c,width=width)
        for d in drives:
            tree.insert("", "end", values=(d.get("Drive",""),d.get("VolumeName",""),d.get("FileSystem",""),format_bytes(d.get("SizeBytes")),format_bytes(d.get("FreeBytes"))))
        tree.pack(fill="both", expand=True, pady=8)

    def _build_files_tab(self):
        f = self._tab("ファイル構造")
        files = self.payload["files"]
        folders = self.payload["folders"]
        row = ttk.Frame(f); row.pack(fill="x")
        self._category_check(row, "folders", f"フォルダー一覧を梱包（{len(folders):,}件）")
        self._category_check(row, "files", f"ファイル名・パス等のメタデータを梱包（{len(files):,}件）")
        ttk.Label(f, text="ファイル名・パスには個人情報が含まれる可能性があります。機微候補は初期状態で除外されます。行をダブルクリックすると梱包対象を切り替えます。", foreground="#a05a00", wraplength=980).pack(anchor="w", pady=6)
        folder_frame = ttk.LabelFrame(f, text=f"フォルダー一覧（{len(folders):,} 件）", padding=5)
        folder_frame.pack(fill="x", pady=(0,6))
        fsearch = ttk.Frame(folder_frame); fsearch.pack(fill="x", pady=(0,4))
        if not hasattr(self, "folder_search_var"):
            self.folder_search_var = StringVar()
        ttk.Label(fsearch, text="フォルダー検索：").pack(side="left")
        fent = ttk.Entry(fsearch, textvariable=self.folder_search_var, width=36); fent.pack(side="left", padx=4)
        fent.bind("<KeyRelease>", lambda _e: self._reset_folder_page())
        ttk.Button(fsearch, text="表示ページをすべて含める", command=lambda: self._set_visible_folders(True)).pack(side="left", padx=3)
        ttk.Button(fsearch, text="表示ページをすべて除外", command=lambda: self._set_visible_folders(False)).pack(side="left", padx=3)
        self.folder_page_label = ttk.Label(fsearch, text="")
        self.folder_page_label.pack(side="right", padx=4)
        ttk.Button(fsearch, text="次へ", command=lambda: self._move_folder_page(1)).pack(side="right", padx=2)
        ttk.Button(fsearch, text="前へ", command=lambda: self._move_folder_page(-1)).pack(side="right", padx=2)
        self.folder_tree = ttk.Treeview(folder_frame, columns=("include","drive","path","depth"), show="headings", height=6)
        for c, title, width in [("include","梱包",60),("drive","ドライブ",70),("path","フォルダー（匿名化）",700),("depth","階層",60)]:
            self.folder_tree.heading(c, text=title); self.folder_tree.column(c, width=width, stretch=(c == "path"))
        folder_table = ttk.Frame(folder_frame); folder_table.pack(fill="x")
        folder_scroll = ttk.Scrollbar(folder_table, orient="vertical", command=self.folder_tree.yview)
        self.folder_tree.configure(yscrollcommand=folder_scroll.set)
        self.folder_tree.pack(side="left", fill="x", expand=True)
        folder_scroll.pack(side="right", fill="y")
        self.folder_tree.bind("<Double-1>", self._toggle_selected_folder)
        self.folder_rows = []
        self._refresh_folder_tree()
        if len(folders) > FOLDER_PAGE_SIZE:
            ttk.Label(folder_frame, text=f"ページ移動で全件を確認できます（1ページ {FOLDER_PAGE_SIZE} 件）。行をダブルクリックすると個別に含める／除外を切り替えます。", foreground="#777").pack(anchor="w")
        search = ttk.Frame(f); search.pack(fill="x", pady=(0,6))
        ttk.Label(search, text="名前・パス検索：").pack(side="left")
        ent = ttk.Entry(search, textvariable=self.file_search_var, width=45); ent.pack(side="left", padx=5)
        ent.bind("<KeyRelease>", lambda _e: self._reset_file_page())
        ttk.Button(search, text="表示ページをすべて含める", command=lambda: self._set_visible_files(True)).pack(side="left", padx=4)
        ttk.Button(search, text="表示ページをすべて除外", command=lambda: self._set_visible_files(False)).pack(side="left", padx=4)
        self.file_page_label = ttk.Label(search, text="")
        self.file_page_label.pack(side="right", padx=4)
        ttk.Button(search, text="次へ", command=lambda: self._move_file_page(1)).pack(side="right", padx=2)
        ttk.Button(search, text="前へ", command=lambda: self._move_file_page(-1)).pack(side="right", padx=2)
        # Keep the Treeview and its scrollbars inside file_table. The parent tab `f`
        # uses pack() for its direct children; mixing grid() and pack() on that same
        # parent raises TclError during ReviewWindow construction.
        file_table = ttk.Frame(f)
        file_table.pack(fill="both", expand=True)
        self.file_tree = ttk.Treeview(file_table, columns=("include","name","extension","size","modified","privacy","path"), show="headings", selectmode="extended")
        cols = [("include","梱包",65),("name","名前",200),("extension","拡張子",90),("size","サイズ",100),("modified","更新日時",160),("privacy","機微候補",100),("path","パス（匿名化）",500)]
        for c,title,w in cols:
            self.file_tree.heading(c,text=title); self.file_tree.column(c,width=w,stretch=(c in ("name","path")))
        file_vscroll = ttk.Scrollbar(file_table, orient="vertical", command=self.file_tree.yview)
        file_hscroll = ttk.Scrollbar(file_table, orient="horizontal", command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=file_vscroll.set, xscrollcommand=file_hscroll.set)
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        file_vscroll.grid(row=0, column=1, sticky="ns")
        file_hscroll.grid(row=1, column=0, sticky="ew")
        file_table.grid_rowconfigure(0, weight=1)
        file_table.grid_columnconfigure(0, weight=1)
        self.file_tree.bind("<Double-1>", self._toggle_selected_file)
        self._refresh_file_tree()
        self.file_hint = ttk.Label(f, text="", foreground="#555"); self.file_hint.pack(anchor="w", pady=(5,0))
        self._update_file_hint()

    def _visible_folder_rows(self):
        query = self.folder_search_var.get().strip().casefold()
        rows = self.payload["folders"]
        if query:
            rows = [r for r in rows if query in r["Path"].casefold() or query in r["Drive"].casefold()]
        pages = max(1, (len(rows) + FOLDER_PAGE_SIZE - 1) // FOLDER_PAGE_SIZE)
        self.folder_page = min(max(0, self.folder_page), pages - 1)
        start = self.folder_page * FOLDER_PAGE_SIZE
        return rows[start:start + FOLDER_PAGE_SIZE]

    def _refresh_folder_tree(self):
        if not hasattr(self, "folder_tree"):
            return
        self.folder_tree.delete(*self.folder_tree.get_children())
        self.folder_rows = self._visible_folder_rows()
        for i, r in enumerate(self.folder_rows):
            self.folder_tree.insert("", "end", iid=str(i), values=(self.t("はい") if r.get("Include",False) else self.t("いいえ"),r.get("Drive",""),r.get("Path",""),r.get("Depth",0)))
        query = self.folder_search_var.get().strip().casefold()
        total = len(self.payload["folders"])
        if query:
            total = sum(1 for r in self.payload["folders"] if query in r["Path"].casefold() or query in r["Drive"].casefold())
        pages = max(1, (total + FOLDER_PAGE_SIZE - 1) // FOLDER_PAGE_SIZE)
        included = sum(1 for r in self.payload["folders"] if r.get("Include",False))
        self.folder_page_label.configure(text=self.t(f"検索結果 {total:,} / 選択 {included:,} / {self.folder_page+1}/{pages}"))

    def _reset_folder_page(self):
        self.folder_page = 0
        self._refresh_folder_tree()

    def _move_folder_page(self, delta):
        self.folder_page += delta
        self._refresh_folder_tree()

    def _toggle_selected_folder(self, event):
        item = self.folder_tree.identify_row(event.y)
        if not item: return
        try:
            row = self.folder_rows[int(item)]
            row["Include"] = not row.get("Include", False)
            vals = list(self.folder_tree.item(item, "values")); vals[0] = self.t("はい") if row["Include"] else self.t("いいえ")
            self.folder_tree.item(item, values=vals)
        except (IndexError, ValueError):
            return

    def _set_visible_folders(self, value):
        for row in self.folder_rows:
            row["Include"] = value
        self._refresh_folder_tree()

    def _visible_file_rows(self):
        query = self.file_search_var.get().strip().casefold()
        rows = self.payload["files"]
        if query:
            rows = [r for r in rows if query in r["Name"].casefold() or query in r["Path"].casefold() or query in r["Extension"].casefold()]
        pages = max(1, (len(rows) + FILE_PAGE_SIZE - 1) // FILE_PAGE_SIZE)
        self.file_page = min(max(0, self.file_page), pages - 1)
        start = self.file_page * FILE_PAGE_SIZE
        return rows[start:start + FILE_PAGE_SIZE]

    def _refresh_file_tree(self):
        if not hasattr(self, "file_tree"):
            return
        self.file_tree.delete(*self.file_tree.get_children())
        self.file_page_rows = self._visible_file_rows()
        for i, r in enumerate(self.file_page_rows):
            self.file_tree.insert("", "end", iid=str(i), values=(self.t("はい") if r.get("Include") else self.t("いいえ"), r["Name"], r["Extension"], format_bytes(r["SizeBytes"]), r["Modified"], self.t(r["PrivacyCandidate"]), r["Path"]))
        self._update_file_hint()
        query = self.file_search_var.get().strip().casefold()
        total = len(self.payload["files"])
        if query:
            total = sum(1 for r in self.payload["files"] if query in r["Name"].casefold() or query in r["Path"].casefold() or query in r["Extension"].casefold())
        pages = max(1, (total + FILE_PAGE_SIZE - 1) // FILE_PAGE_SIZE)
        if hasattr(self, "file_page_label"):
            self.file_page_label.configure(text=self.t(f"検索結果 {total:,} / 選択 {sum(1 for r in self.payload['files'] if r.get('Include',False)):,} / {self.file_page+1}/{pages}"))

    def _reset_file_page(self):
        self.file_page = 0
        self._refresh_file_tree()

    def _move_file_page(self, delta):
        self.file_page += delta
        self._refresh_file_tree()

    def _update_file_hint(self):
        if hasattr(self, "file_hint"):
            total = len(self.payload["files"])
            shown = len(self.file_page_rows)
            included = sum(1 for r in self.payload["files"] if r.get("Include"))
            self.file_hint.configure(text=self.t(f"表示 {shown:,} 件 / 全体 {total:,} 件 / 現在の選択 {included:,} 件。検索・ページ移動で全件を確認できます。1ページ {FILE_PAGE_SIZE} 件です。"))

    def _toggle_selected_file(self, event=None):
        item = self.file_tree.identify_row(event.y) if event else None
        if not item:
            sel = self.file_tree.selection()
            if not sel: return
            item = sel[0]
        try:
            row = self.file_page_rows[int(item)]
            row["Include"] = not row.get("Include", False)
            self._refresh_file_tree()
        except (IndexError, ValueError):
            return

    def _set_visible_files(self, value):
        for row in self.file_page_rows:
            if value and row.get("PrivacyCandidate") == "Yes":
                continue
            row["Include"] = value
        self._refresh_file_tree()

    def _build_warnings_tab(self):
        f = self._tab("除外・未取得")
        counts = self.payload["filesystem_counts"]
        self._category_check(f, "security", f"除外理由の集計を梱包する（検出 {len(self.payload.get('exclusions',[])):,} 件）")
        warning_total = len(self.payload.get("warnings", [])) + len(self.payload.get("scan_warnings", []))
        self._category_check(f, "warnings", f"スキャン警告を梱包する（{warning_total:,} 件）")
        text = (
            f"{self.t('スキップされた項目：')}{counts['skipped']:,} {self.t('件')}\n"
            f"{self.t('アクセス／メタデータ取得エラー：')}{counts['errors']:,} {self.t('件')}\n"
            f"{self.t('ファイル：')}{counts['files']:,} {self.t('件')}\n{self.t('フォルダー：')}{counts['folders']:,} {self.t('件')}\n"
            f"{self.t('スキャン状態：')}{self.t(self.payload.get('filesystem_status'))}\n\n"
            f"{self.t('OS・アプリケーションの保護領域、隠し／システムフォルダー、資格情報候補のフォルダー、再解析ポイントは走査しません。')}"
        )
        ttk.Label(f, text=text, justify="left").pack(anchor="nw", fill="x", pady=12)
        ttk.Label(f, text="スキャン警告CSVにはドライブ文字とエラー種別だけを記録します。個別のファイルパスは出力しません。", foreground="#a05a00", wraplength=950).pack(anchor="w")

    def _approve(self):
        if not any(v.get() for v in self.categories.values()):
            messagebox.showwarning(self.t("梱包対象なし"), self.t("少なくとも1つのカテゴリを選択してください。"), parent=self)
            return
        selected_file_count = sum(1 for r in self.payload["files"] if r.get("Include")) if self.categories["files"].get() else 0
        software_count = sum(1 for r in self.payload["system"].get("software", []) if r.get("Include", False)) if self.categories["software"].get() else 0
        drive_count = len(self.payload["system"].get("drives", [])) if self.categories["drives"].get() else 0
        folder_count = sum(1 for r in self.payload["folders"] if r.get("Include")) if self.categories["folders"].get() else 0
        summary = [
            f"{self.t('PC基本情報')}：{self.t('含む') if self.categories['system'].get() else self.t('除外')}",
            f"{self.t('ソフトウェア')}：{software_count:,} {self.t('件')}",
            f"{self.t('ストレージ')}：{drive_count:,} {self.t('件')}",
            f"{self.t('フォルダー')}：{folder_count:,} {self.t('件')}",
            f"{self.t('ファイルメタデータ')}：{selected_file_count:,} {self.t('件')}",
            f"{self.t('警告')}：{self.t('含む') if self.categories['warnings'].get() else self.t('除外')}",
            f"{self.t('除外集計')}：{self.t('含む') if self.categories['security'].get() else self.t('除外')}",
        ]
        msg = self.t("以下の内容でAI向けZIPを作成します。") + "\n\n" + "\n".join(summary) + "\n\n" + self.t("ZIP内のファイル名・パス・メタデータは閲覧可能です。個人情報が含まれていないことを確認しましたか？")
        if not messagebox.askyesno(self.t("最終確認"), msg, parent=self):
            return
        sensitive_included = sum(1 for r in self.payload["files"] if r.get("Include") and r.get("PrivacyCandidate") == "Yes") if self.categories["files"].get() else 0
        if sensitive_included:
            warning = f"\n\n{self.t('警告：機微候補として検出されたファイル名が')} {sensitive_included:,} {self.t('件')}"
            if self.language == "zh":
                warning += "。请仅保留确实需要的项目。"
            elif self.language == "ko":
                warning += " 포함됩니다. 필요한 항목만 남겨 주세요."
            elif self.language == "en":
                warning += " sensitive-candidate file names are included. Keep only what you need."
            else:
                warning += " 含まれます。必要なものだけを残してください。"
            msg += warning
            if not messagebox.askyesno(self.t("機微候補の最終確認"), msg + "\n\n" + self.t("この内容で続行しますか？"), parent=self):
                return
        self.result = {"categories": {k:v.get() for k,v in self.categories.items()}, "language": self.language}
        result = self.result
        if self.on_confirm(result, self):
            self._close_review()



def discover_fixed_drives_fast():
    """Return local fixed-drive roots only; does not open drive contents."""
    if not is_windows():
        return []
    roots = []
    try:
        kernel32 = ctypes.windll.kernel32
        mask = kernel32.GetLogicalDrives()
        for i in range(26):
            if mask & (1 << i):
                root = chr(65 + i) + ":\\"
                if kernel32.GetDriveTypeW(ctypes.c_wchar_p(root)) == 3 and os.path.isdir(root):
                    roots.append(root)
    except Exception:
        # Fallback to a lightweight PowerShell logical-drive query.
        try:
            raw = run_powershell_json("@(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object -ExpandProperty DeviceID) | ConvertTo-Json -Compress")
            values = raw if isinstance(raw, list) else [raw]
            roots = [str(x).strip() + "\\" for x in values if x]
        except Exception:
            return []
    return roots


class DriveSelection(Toplevel):
    def __init__(self, master, drives, language="ja"):
        super().__init__(master)
        self.master_window = master
        self.drives = list(drives)
        self.language = language
        self.title(tr("スキャン対象ドライブの選択", self.language))
        self.resizable(False, False)
        self.result = None
        self.vars = {drive: BooleanVar(value=True) for drive in self.drives}
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx()+80}+{master.winfo_rooty()+80}")
        # Deliberately modeless at the native-window level. App disables its
        # scan button while this selector is open; no transient/grab lock.
        self.after(100, self._activate_window)

    def t(self, text):
        return tr(text, self.language)

    def set_language(self, language):
        self.language = language
        self.title(self.t("スキャン対象ドライブの選択"))
        self._build()

    def _build(self):
        old_container = getattr(self, "container", None)
        if old_container is not None:
            try:
                old_container.destroy()
            except Exception:
                pass
        body = ttk.Frame(self, padding=18)
        self.container = body
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="スキャンするローカル固定ドライブを選択してください。", font=ui_font(self.language, 11, "bold")).pack(anchor="w")
        ttk.Label(body, text="ローカル固定ドライブのみを表示します。ネットワークドライブやリムーバブルドライブは通常対象外です。USB SSDなどでもWindowsが固定ドライブとして報告する場合は表示されます。", wraplength=460).pack(anchor="w", pady=(5,12))
        for drive in self.drives:
            ttk.Checkbutton(body, text=drive, variable=self.vars[drive]).pack(anchor="w", pady=2)
        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=(16,0))
        ttk.Button(btns, text="キャンセル", command=self._cancel).pack(side="right", padx=(5,0))
        ttk.Button(btns, text="この範囲でスキャン", command=self._accept).pack(side="right")
        translate_widget_tree(self.container, self.language)

    def _activate_window(self):
        try:
            if self.winfo_exists():
                if self.state() == "iconic":
                    self.deiconify()
                self.lift()
                self.focus_force()
        except Exception:
            pass

    def _cancel(self):
        self.result = None
        try:
            self.destroy()
        except Exception:
            pass

    def _accept(self):
        selected = [drive for drive, var in self.vars.items() if var.get()]
        if not selected:
            messagebox.showwarning(self.t("対象ドライブなし"), self.t("少なくとも1つのドライブを選択してください。"), parent=self)
            return
        self.result = selected
        self.destroy()


class App:
    def __init__(self, root):
        self.root = root
        self.language = load_language_preference()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("900x650")
        self.root.minsize(760, 560)
        self.q = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker = None
        self.payload = None
        self.selected_roots = []
        self.drive_dialog = None
        self.review_window = None
        self.status = StringVar(value=tr("スキャン開始前です。", self.language))
        self.progress = StringVar(value="")
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._request_close)
        self.root.after(100, self._activate_main_window)
        self.root.after(200, self._poll)

    def t(self, text):
        return tr(text, self.language)

    def _change_language(self, _event=None):
        selected = LANGUAGE_CODES_BY_NAME.get(self.language_var.get())
        if not selected or selected == self.language:
            return
        self.language = selected
        try:
            save_language_preference(self.language)
        except OSError:
            pass
        if self.worker and self.worker.is_alive():
            self.status.set(self.t("スキャンを開始しています..."))
        elif self.payload is not None:
            self.status.set(self.t("スキャンが終了しました。収集結果を確認してください。"))
        else:
            self.status.set(self.t("スキャン開始前です。"))
        self.progress.set("")
        self._build()
        if self.worker and self.worker.is_alive():
            self.start_btn.configure(state="disabled")
            self.cancel_btn.configure(state="normal")
        elif self.review_window is not None:
            try:
                if self.review_window.winfo_exists():
                    self.start_btn.configure(state="disabled")
            except Exception:
                self.review_window = None
        if self.review_window is not None:
            try:
                if self.review_window.winfo_exists():
                    self.review_window.set_language(self.language)
            except Exception:
                self.review_window = None
        if self.drive_dialog is not None:
            try:
                if self.drive_dialog.winfo_exists():
                    self.drive_dialog.set_language(self.language)
            except Exception:
                self.drive_dialog = None

    def _activate_main_window(self):
        try:
            if self.root.winfo_exists():
                if self.root.state() == "iconic":
                    self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
        except Exception:
            pass

    def _on_review_closed(self, window):
        if self.review_window is window:
            self.review_window = None
        try:
            if self.root.winfo_exists():
                self.start_btn.configure(state="normal")
        except Exception:
            pass

    def _request_close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno(self.t("終了確認"), self.t("スキャン中です。停止してアプリを終了しますか？"), parent=self.root):
                return
            self.cancel_event.set()
            self.status.set(self.t("スキャンを停止して終了しています..."))
            self.root.after(200, self._finish_close_when_stopped)
        else:
            self.root.destroy()

    def _finish_close_when_stopped(self):
        if self.worker and self.worker.is_alive():
            self.root.after(200, self._finish_close_when_stopped)
        else:
            self.root.destroy()

    def _build(self):
        old_container = getattr(self, "container", None)
        if old_container is not None:
            try:
                old_container.destroy()
            except Exception:
                pass
        self.container = ttk.Frame(self.root, padding=20)
        outer = self.container
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="PC Context Builder", font=ui_font(self.language, 24, "bold")).pack(side="left", anchor="w")
        language_bar = ttk.Frame(header)
        language_bar.pack(side="right", anchor="e", padx=(8,0), pady=4)
        ttk.Label(language_bar, text="言語 / Language").pack(side="left", padx=(0,6))
        self.language_var = StringVar(value=LANGUAGE_NAMES[self.language])
        self.language_combo = ttk.Combobox(
            language_bar, textvariable=self.language_var,
            values=[LANGUAGE_NAMES[code] for code in LANGUAGE_ORDER],
            state="readonly", width=12
        )
        self.language_combo.pack(side="left")
        self.language_combo.bind("<<ComboboxSelected>>", self._change_language)
        ttk.Label(outer, text="Windows PCの環境情報を収集し、確認後にAIアシスタント向けコンテキストパッケージを作成します。", font=ui_font(self.language, 10), wraplength=820).pack(anchor="w", pady=(4,14))
        tags = ttk.Frame(outer); tags.pack(anchor="w", pady=(0,14))
        ttk.Label(tags, text="ローカル処理", relief="solid", padding=(8,4)).pack(side="left", padx=(0,6))
        ttk.Label(tags, text="読み取り専用", relief="solid", padding=(8,4)).pack(side="left", padx=6)
        ttk.Label(tags, text="ファイル本文は取得しない", relief="solid", padding=(8,4)).pack(side="left", padx=6)
        card = ttk.LabelFrame(outer, text="今回のスキャン範囲", padding=14)
        card.pack(fill="x", pady=8)
        details = [
            "Windows・CPU・メモリ・GPU・ディスプレイ情報",
            "インストール済みソフトウェア・Python環境・ブラウザー情報",
            "ローカル固定ドライブの容量情報",
            "ファイル名・パス・サイズ・更新日時（内容は読まない）",
            "保護領域・資格情報候補・隠しフォルダー・リンク先は除外",
        ]
        for line in details:
            # Translate the source string before adding the bullet prefix; otherwise
            # exact-key lookup cannot match the prefixed Japanese text.
            ttk.Label(card, text="• " + self.t(line)).pack(anchor="w", pady=2)
        warning = ttk.LabelFrame(outer, text="プライバシー保護", padding=14)
        warning.pack(fill="x", pady=8)
        ttk.Label(warning, text="スキャンとZIP生成はPC内で実行します。自動アップロードやネットワーク送信は行いません。ファイル名・パスも個人情報になり得るため、収集結果を確認してから梱包してください。", wraplength=820, justify="left").pack(anchor="w")
        actions = ttk.Frame(outer); actions.pack(fill="x", pady=(16,8))
        self.start_btn = ttk.Button(actions, text="PC全体の概要をスキャン", command=self.start_scan)
        self.start_btn.pack(side="left")
        self.cancel_btn = ttk.Button(actions, text="スキャンを停止", command=self.cancel_scan, state="disabled")
        self.cancel_btn.pack(side="left", padx=8)
        ttk.Label(outer, textvariable=self.status, font=ui_font(self.language, 10, "bold")).pack(anchor="w", pady=(8,2))
        ttk.Label(outer, textvariable=self.progress, foreground="#555").pack(anchor="w")
        self.pb = ttk.Progressbar(outer, mode="indeterminate")
        self.pb.pack(fill="x", pady=8)
        note = ttk.LabelFrame(outer, text="重要な注意", padding=12)
        note.pack(fill="x", pady=8)
        ttk.Label(note, text="• スキャン前に許可を求め、結果一覧の確認と最終承認が終わるまでZIPを作成しません。\n• スキャンは最大10分、最大150,000ファイル・30,000フォルダーで上限を設けます。上限に達した場合は部分スキャンとして記録します。\n• 生成ZIPは通常のZIPです。暗号化されていないため、共有する前に内容を確認してください。", justify="left").pack(anchor="w")
        ttk.Label(outer, text=f"v{VERSION} • Python標準ライブラリのみ • Windows 11 x64", foreground="#666").pack(anchor="e", pady=(10,0))
        translate_widget_tree(self.container, self.language)

    def start_scan(self):
        if self.review_window is not None:
            try:
                if self.review_window.winfo_exists():
                    self.review_window.lift()
                    self.review_window.focus_force()
                    return
            except Exception:
                self.review_window = None
        if not is_windows():
            messagebox.showerror(self.t("Windows専用"), self.t("このアプリはWindows 11上で実行してください。"), parent=self.root)
            return
        if sys.version_info[:2] != (3,14) or sys.maxsize <= 2**32:
            messagebox.showerror(self.t("実行環境が違います"), self.t("Python 3.14 x64が必要です。") + f"\n{self.t('現在：')}{sys.version.split()[0]} / {'64-bit' if sys.maxsize>2**32 else '32-bit'}", parent=self.root)
            return
        if not messagebox.askyesno(self.t("スキャン開始の確認"), self.t("ローカルPCのシステム情報・ソフトウェア情報・ドライブ情報・ファイルのメタデータを読み取り専用で調査します。\n\nファイルの中身、パスワード、Cookie、APIキーは読み取りません。\n\n続けて対象ドライブを選択します。開始しますか？"), parent=self.root):
            return
        drives = discover_fixed_drives_fast()
        if not drives:
            messagebox.showerror(self.t("ドライブを検出できません"), self.t("ローカル固定ドライブを取得できませんでした。"), parent=self.root)
            return
        # Prevent a second selector or duplicate scan without using a Tk grab.
        self.start_btn.configure(state="disabled")
        chooser = DriveSelection(self.root, drives, self.language)
        self.drive_dialog = chooser
        self.root.wait_window(chooser)
        self.drive_dialog = None
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
        if not chooser.result:
            self.start_btn.configure(state="normal")
            return
        self.selected_roots = chooser.result
        self.cancel_event.clear()
        self.cancel_btn.configure(state="normal")
        self.status.set(self.t("スキャンを開始しています..."))
        self.progress.set("")
        self.pb.start(10)
        self.worker = threading.Thread(target=self._scan_worker, daemon=True)
        self.worker.start()

    def _scan_worker(self):
        try:
            create_scan_payload(self.q, self.cancel_event, self.selected_roots)
        except InterruptedError:
            self.q.put(("cancelled", None))
        except Exception as exc:
            self.q.put(("error", f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}"))

    def cancel_scan(self):
        self.cancel_event.set()
        self.status.set(self.t("停止要求を送信しました。現在の項目を安全に終了しています..."))
        self.cancel_btn.configure(state="disabled")

    def _poll(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "status":
                    self.status.set(self.t(data))
                elif kind == "progress":
                    self.progress.set(self.t(f"ファイル {data['files']:,} / フォルダー {data['folders']:,} / 除外 {data['skipped']:,} / エラー {data['errors']:,} — {data['current']}"))
                elif kind == "cancelled":
                    self.pb.stop()
                    self.start_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                    self.status.set(self.t("スキャンをキャンセルしました。ZIPは作成していません。"))
                    self.progress.set("")
                elif kind == "done":
                    self.payload = data
                    self.pb.stop()
                    self.start_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                    self.status.set(self.t("スキャンが終了しました。収集結果を確認してください。"))
                    self.progress.set(self.t(f"ファイル {len(data['files']):,} 件 / フォルダー {len(data['folders']):,} 件 / 状態 {self.t(data['filesystem_status'])}"))
                    self.start_btn.configure(state="disabled")
                    self.review_window = ReviewWindow(self.root, self.payload, self.create_zip, self.language)
                    self.review_window.set_on_close(self._on_review_closed)
                elif kind == "error":
                    self.pb.stop()
                    self.start_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                    self.status.set(self.t("スキャンに失敗しました。"))
                    messagebox.showerror(self.t("スキャンエラー"), data[-5000:], parent=self.root)
        except queue.Empty:
            pass
        self.root.after(200, self._poll)

    def create_zip(self, choices, review_window=None):
        dialog_parent = review_window or self.root
        output = filedialog.askdirectory(title=self.t("AI向けZIPの出力先を選択してください"), mustexist=True, parent=dialog_parent)
        if not output:
            messagebox.showinfo(self.t("キャンセル"), self.t("出力先が選択されなかったため、ZIPは作成していません。レビュー画面に戻ります。"), parent=dialog_parent)
            return False
        try:
            self.status.set(self.t("AI向けZIPを作成し、整合性を検査しています..."))
            self.root.update_idletasks()
            path, counts, size = build_package(self.payload, choices, output, self.language)
            self.status.set(self.t("ZIPの作成と整合性検査が完了しました。"))
            self.progress.set(path)
            count_labels = {
                "system": "PC基本情報", "software": "ソフトウェア", "drives": "ストレージ",
                "folders": "フォルダー", "files": "ファイルメタデータ",
                "warnings": "警告", "security": "除外集計",
            }
            count_lines = [
                f"{self.t(count_labels.get(key, key))}: {value:,}"
                for key, value in counts.items()
            ]
            success_message = (
                f"{self.t('AI向けZIPを作成しました。')}\n\n"
                f"{self.t('保存先：')}{path}\n"
                f"{self.t('サイズ：')}{format_bytes(size)}\n\n"
                f"{self.t('収録件数：')}\n" + "\n".join(count_lines) +
                f"\n\n{self.t('ZIPの中身を確認してからAIアシスタントに共有してください。')}"
            )
            messagebox.showinfo(self.t("作成完了"), success_message, parent=dialog_parent)
            return True
        except Exception as exc:
            self.status.set(self.t("ZIPの作成に失敗しました。"))
            messagebox.showerror(self.t("ZIP作成エラー"), f"{type(exc).__name__}: {exc}", parent=dialog_parent)
            return False


def self_test():
    import tempfile
    import io

    assert tr("PC概要", "zh") == "电脑概况"
    assert tr("PC概要", "ja") == "PC概要"
    assert tr("PC概要", "ko") == "PC 개요"
    assert tr("PC概要", "en") == "PC overview"
    # UI localization regressions: every scan-scope bullet and overview row label
    # must resolve through the selected locale, not remain Japanese source copy.
    scan_scope_keys = (
        "Windows・CPU・メモリ・GPU・ディスプレイ情報",
        "インストール済みソフトウェア・Python環境・ブラウザー情報",
        "ローカル固定ドライブの容量情報",
        "ファイル名・パス・サイズ・更新日時（内容は読まない）",
        "保護領域・資格情報候補・隠しフォルダー・リンク先は除外",
    )
    scan_scope_zh = (
        "Windows、CPU、内存、GPU 和显示器信息",
        "已安装软件、Python 环境和浏览器信息",
        "本地固定驱动器容量信息",
        "文件名、路径、大小和修改时间（不读取文件内容）",
        "排除受保护区域、可能包含凭据的目录、隐藏文件夹和链接目标",
    )
    assert tuple(tr(key, "zh") for key in scan_scope_keys) == scan_scope_zh
    overview_label_zh = {
        "メーカー・モデル": "制造商／型号", "マザーボード": "主板",
        "メモリ": "内存", "ディスプレイ": "显示器", "ブラウザー": "浏览器",
        "項目": "项目", "取得値": "获取值",
    }
    assert all(tr(key, "zh") == value for key, value in overview_label_zh.items())
    assert tr("Collection method: local read-only inventory", "zh") == "收集方式：本地只读清单"
    assert tr("- PC profile: included (1 records)", "en") == "- PC profile: included (1 records)"

    assert is_sensitive_name(".env")
    assert is_sensitive_name("my_api_key.txt")
    assert is_sensitive_name("adbkey", r"C:\Users\Example\.android\adbkey")
    assert is_sensitive_name("adbkey.pub", r"C:\Users\Example\.android\adbkey.pub")
    assert not is_sensitive_name("vacation.jpg")

    # CSV values originating from file names, paths, and registry metadata must
    # not become spreadsheet formulas when opened by common spreadsheet apps.
    formula_cells = ("=1+1", "+SUM(1,1)", "-1+2", "@SUM(1,1)", "  =1+1", "\t=1+1", "\r\n=1+1", "\ufeff=1+1")
    for value in formula_cells:
        assert sanitize_csv_cell(value) == "'" + value
    for value in ("normal.txt", "2026-11-10T12:00:00+09:00", "ordinary text"):
        assert sanitize_csv_cell(value) == value
    assert sanitize_csv_cell(12345) == 12345
    parsed_csv = list(csv.DictReader(io.StringIO(csv_bytes([{"Value": "=1+1"}, {"Value": "safe"}], ["Value"]).decode("utf-8-sig"))))
    assert parsed_csv[0]["Value"] == "'=1+1" and parsed_csv[1]["Value"] == "safe"

    # Sensitive paths support multi-component entries such as .config/gcloud.
    assert is_sensitive_dir("gcloud", r"C:\\Users\\Example\\.config\\gcloud")
    assert not is_sensitive_dir("gcloudish", r"C:\\Users\\Example\\.config\\gcloudish")
    assert is_cloud_sync_directory("OneDrive - Contoso", r"C:\\Users\\Example\\OneDrive - Contoso")

    # The PowerShell collector must drain both pipes while the child process is
    # running. This regression emits much more than a typical Windows pipe buffer
    # to stdout and stderr before it exits.
    noisy_code = (
        "import sys; "
        "sys.stdout.write('O' * 1048576); sys.stdout.flush(); "
        "sys.stderr.write('E' * 1048576); sys.stderr.flush(); "
        "sys.stdout.write('\\nJSON_END\\n'); sys.stdout.flush()"
    )
    noisy_proc = subprocess.Popen(
        [sys.executable, "-c", noisy_code], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace"
    )
    noisy_out, noisy_err = _communicate_with_timeout(noisy_proc, timeout=10)
    assert noisy_proc.returncode == 0
    assert len(noisy_out) >= 1048576 and "JSON_END" in noisy_out
    assert len(noisy_err) >= 1048576 and set(noisy_err) == {"E"}

    # Native RAM API is used when CIM does not provide physical memory.
    original_memory_reader = get_physical_memory_bytes
    try:
        globals()["get_physical_memory_bytes"] = lambda: 8 * 1024**3
        fallback = get_python_fallback_system([])
        assert fallback["Computer"]["TotalPhysicalMemory"] == 8 * 1024**3
        normalized = normalize_system_result({"OS": {}, "Computer": {"TotalPhysicalMemory": None}, "CPU": [], "GPU": [], "BaseBoard": {"Manufacturer":"TestBoard"}})
        assert normalized["hardware"]["physical_memory_bytes"] == 8 * 1024**3
        assert normalized["hardware"]["motherboard_manufacturer"] == "TestBoard"
    finally:
        globals()["get_physical_memory_bytes"] = original_memory_reader

    # Protected Windows system directories that deny access are expected skips,
    # not scan errors that downgrade an otherwise complete scan.
    assert is_expected_protected_directory_path(r"C:\$Recycle.Bin")
    assert is_expected_protected_directory_path(r"C:\System Volume Information\IndexerVolumeGuid")
    assert not is_expected_protected_directory_path(r"C:\Users\Example\Documents")
    with tempfile.TemporaryDirectory() as td_protected:
        protected_root = Path(td_protected) / "$Recycle.Bin"
        protected_root.mkdir()
        protected_q = queue.Queue()
        with __import__("unittest.mock", fromlist=["patch"]).patch("os.scandir", side_effect=PermissionError("synthetic protected folder")):
            scan_filesystem([str(protected_root)], protected_q, threading.Event())
        protected_done = [item[1] for item in list(protected_q.queue) if item[0] == "filesystem_done"][0]
        assert protected_done["status"] == "completed"
        assert protected_done["counts"]["errors"] == 0
        assert protected_done["counts"]["skipped"] == 1

    # The review action footer must be a fixed grid row, not clipped by the
    # expanding Notebook. Verify the bottom ZIP action is wired to _approve.
    import inspect
    review_build_source = inspect.getsource(ReviewWindow._build)
    assert 'outer.rowconfigure(1, weight=1)' in review_build_source
    assert 'top.grid(row=0, column=0, sticky="ew")' in review_build_source
    assert 'self.nb.grid(row=1, column=0, sticky="nsew"' in review_build_source
    assert 'bottom.grid(row=2, column=0, sticky="ew")' in review_build_source
    assert 'text="梱包内容を確認してZIP作成へ", command=self._approve' in review_build_source
    # Windows GUI safety checks: no transient/grab modal locks, and all
    # native message boxes must be explicitly parented to their owning window.
    review_init_source = inspect.getsource(ReviewWindow.__init__)
    drive_init_source = inspect.getsource(DriveSelection.__init__)
    app_init_source = inspect.getsource(App.__init__)
    assert 'self.after(100, self._activate_window)' in review_init_source
    assert 'self.after(100, self._activate_window)' in drive_init_source
    assert 'self.root.after(100, self._activate_main_window)' in app_init_source
    review_activate_source = inspect.getsource(ReviewWindow._activate_window)
    drive_activate_source = inspect.getsource(DriveSelection._activate_window)
    main_activate_source = inspect.getsource(App._activate_main_window)
    for activation_source in (review_activate_source, drive_activate_source, main_activate_source):
        assert '.lift()' in activation_source and '.focus_force()' in activation_source

    import ast
    source_text = Path(__file__).read_text(encoding="utf-8")
    parsed = ast.parse(source_text)
    forbidden_calls = {"transient", "grab_set", "grab_release"}
    messagebox_calls = {"askyesno", "askyesnocancel", "askokcancel", "askretrycancel", "askquestion", "showerror", "showinfo", "showwarning"}
    for node in ast.walk(parsed):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in forbidden_calls:
            raise AssertionError(f"Forbidden Tk modal lock call: {node.func.attr}")
        if isinstance(node.func.value, ast.Name) and node.func.value.id == "messagebox" and node.func.attr in messagebox_calls:
            if not any(keyword.arg == "parent" for keyword in node.keywords):
                raise AssertionError(f"messagebox.{node.func.attr} is missing parent=")
    start_scan_source = inspect.getsource(App.start_scan)
    assert 'parent=self.root' in start_scan_source
    assert 'self.start_btn.configure(state="disabled")' in start_scan_source
    assert 'self.review_window.set_on_close(self._on_review_closed)' in inspect.getsource(App._poll)
    assert should_skip_file("hidden.txt", 0x2, r"C:\\test\\hidden.txt")[0]
    assert should_skip_file("system.dat", 0x4, r"C:\\test\\system.dat")[0]
    assert should_skip_file("link.txt", 0x400, r"C:\\test\\link.txt")[0]
    assert should_skip_dir(".ssh", 0, r"C:\\test\\.ssh")[0]
    assert should_skip_dir("private_notes", 0, r"C:\\test\\private_notes")[0]
    assert not should_skip_file("normal.txt", 0, r"C:\\test\\normal.txt")[0]
    p = mask_path(r"C:\Users\Example\Documents\a.txt")
    assert "%USER%" in p or "%USERPROFILE%" in p
    p2 = mask_path(r"D:\Users\Example\Documents\a.txt")
    assert "%USERPROFILE%" in p2

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "Documents").mkdir()
        (root / "Documents" / "normal.txt").write_text("PRIVATE FILE BODY MUST NEVER ENTER ZIP", encoding="utf-8")
        (root / "Documents" / ".env").write_text("SECRET=DO_NOT_READ", encoding="utf-8")
        (root / "Documents" / "my_api_key.txt").write_text("API_KEY=DO_NOT_READ", encoding="utf-8")
        (root / "private_notes").mkdir()
        (root / "private_notes" / "notes.txt").write_text("DO_NOT_READ", encoding="utf-8")
        (root / ".ssh").mkdir()
        (root / ".ssh" / "id_rsa").write_text("PRIVATE KEY BODY", encoding="utf-8")
        (root / "node_modules").mkdir()
        (root / "node_modules" / "package.json").write_text("{}", encoding="utf-8")
        config_gcloud = root / ".config" / "gcloud"
        config_gcloud.mkdir(parents=True)
        (config_gcloud / "credentials.json").write_text("DO_NOT_SCAN", encoding="utf-8")
        named_sync = root / "OneDrive - Example Org"
        named_sync.mkdir()
        (named_sync / "synced.txt").write_text("DO_NOT_SCAN", encoding="utf-8")
        custom_sync = root / "CustomSyncRoot"
        custom_sync.mkdir()
        (custom_sync / "custom-synced.txt").write_text("DO_NOT_SCAN", encoding="utf-8")
        try:
            os.symlink(root / "Documents", root / "linked_documents", target_is_directory=True)
        except (OSError, NotImplementedError):
            pass

        q = queue.Queue()
        cancel = threading.Event()
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(os.environ, {"OneDrive": str(custom_sync)}, clear=False):
            scan_filesystem([str(root)], q, cancel)
        scan_result = None
        while not q.empty():
            kind, data = q.get_nowait()
            if kind == "filesystem_done":
                scan_result = data
        assert scan_result is not None
        scanned_names = {r["Name"] for r in scan_result["files"]}
        assert "normal.txt" in scanned_names
        assert ".env" in scanned_names and "my_api_key.txt" in scanned_names
        assert all(not r["Include"] for r in scan_result["files"])
        assert next(r for r in scan_result["files"] if r["Name"] == ".env")["PrivacyCandidate"] == "Yes"
        folder_names = {Path(r["Path"]).name.casefold() for r in scan_result["folders"]}
        assert "private_notes" not in folder_names and ".ssh" not in folder_names and "node_modules" not in folder_names
        assert "gcloud" not in folder_names
        assert "onedrive - example org" not in folder_names and "customsyncroot" not in folder_names
        assert all(not r["Include"] for r in scan_result["folders"])
        assert not {"credentials.json", "synced.txt", "custom-synced.txt"} & scanned_names

        safe_file = next(r.copy() for r in scan_result["files"] if r["Name"] == "normal.txt")
        safe_file["Include"] = True
        folder_rows = [r.copy() for r in scan_result["folders"]]
        if folder_rows:
            folder_rows[0]["Include"] = True
        fake = {
            "scan_time": now_iso(),
            "system": {
                "collected_at": now_iso(),
                "os": {"name":"TestOS","version":"1","build":"1","architecture":"x64"},
                "hardware": {"manufacturer":"TestVendor","model":"TestModel","cpu":[],"gpu":[],"display_resolutions":[]},
                "software": [
                    {"Name":"Selected App","Version":"1.0","Publisher":"Example","InstallLocation":"%USERPROFILE%\\Apps\\Selected","Include":True},
                    {"Name":"Excluded App","Version":"2.0","Publisher":"Example","InstallLocation":"C:\\Apps\\Excluded","Include":False},
                ],
                "browser_summary": [{"Name":"Selected App","Version":"1.0"},{"Name":"Excluded App","Version":"2.0"}],
                "python_environments": [],
                "drives": [{"Drive":"C:","VolumeName":"Test","FileSystem":"NTFS","SizeBytes":1000,"FreeBytes":500}],
            },
            "roots": ["C:\\"],
            "files": [safe_file] + [r.copy() for r in scan_result["files"] if r["Name"] != "normal.txt"],
            "folders": folder_rows,
            "warnings": [],
            "scan_warnings": [{"Drive":"local","Reason":"synthetic_warning"}],
            "exclusions": scan_result["exclusions"],
            "filesystem_counts": scan_result["counts"],
            "filesystem_status": scan_result["status"],
            "filesystem_elapsed_seconds": scan_result["elapsed_seconds"],
        }
        choices = {"categories":{"system":True,"software":True,"drives":True,"folders":True,"files":True,"warnings":True,"security":True}}
        path, counts, _ = build_package(fake, choices, td)
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            names = set(z.namelist())
            assert os.path.basename(path).startswith("PC_Context_Pack_")
            assert names and all(name.startswith("PC_Context_Pack/") for name in names)
            assert not any(name.startswith("AI_PC_Knowledge_Pack/") for name in names)
            pack_readme = z.read("PC_Context_Pack/00_README_FOR_AI.md").decode("utf-8-sig")
            assert "# PC Context Pack" in pack_readme
            assert "How an AI assistant should use this package" in pack_readme
        assert "ChatGPT" not in pack_readme
        assert "PC_Context_Pack/00_README_FOR_AI.md" in names
        assert "PC_Context_Pack/04_FILE_INDEX/files.csv" in names
        expected_readme_headings = {
            "zh": ("# PC 上下文资料包", "## 电脑概览", "架构版本："),
            "ja": ("# PC コンテキストパック", "## PC概要", "スキーマバージョン："),
            "ko": ("# PC 컨텍스트 패키지", "## PC 개요", "스키마 버전:"),
            "en": ("# PC Context Pack", "## PC overview", "Schema version:"),
        }
        for language, expected in expected_readme_headings.items():
            localized_path, _, _ = build_package(fake, choices, td, language)
            with zipfile.ZipFile(localized_path) as localized_zip:
                localized_readme = localized_zip.read("PC_Context_Pack/00_README_FOR_AI.md").decode("utf-8-sig")
                localized_manifest = json.loads(localized_zip.read("PC_Context_Pack/06_SCAN_REPORT/manifest.json").decode("utf-8-sig"))
                assert all(value in localized_readme for value in expected), (language, expected)
                assert localized_manifest["ui_language"] == language
                localized_names = set(localized_zip.namelist())
                assert "PC_Context_Pack/00_README_FOR_AI.md" in localized_names
                assert "PC_Context_Pack/04_FILE_INDEX/files.csv" in localized_names
        assert counts["files"] == 1
        with zipfile.ZipFile(path) as z:
            system_text = z.read("PC_Context_Pack/01_PC_PROFILE/system_profile.json").decode("utf-8-sig")
            assert "Selected App" in system_text and "Excluded App" not in system_text
            files_text = z.read("PC_Context_Pack/04_FILE_INDEX/files.csv").decode("utf-8-sig")
            assert "normal.txt" in files_text and ".env" not in files_text and "my_api_key.txt" not in files_text
            warnings_text = z.read("PC_Context_Pack/06_SCAN_REPORT/warnings.csv").decode("utf-8-sig")
            assert "synthetic_warning" in warnings_text
            all_bytes = b"".join(z.read(n) for n in names)
            assert b"PRIVATE FILE BODY MUST NEVER ENTER ZIP" not in all_bytes
            assert b"SECRET=DO_NOT_READ" not in all_bytes
            assert b"API_KEY=DO_NOT_READ" not in all_bytes

        # Category opt-out must remove the corresponding records from every output file.
        path2, counts2, _ = build_package(fake, {"categories":{"system":True,"software":False,"drives":False,"folders":False,"files":False,"warnings":False,"security":False}}, td)
        with zipfile.ZipFile(path2) as z:
            names2 = set(z.namelist())
            assert "PC_Context_Pack/02_SOFTWARE/installed_software.csv" not in names2
            assert "PC_Context_Pack/03_STORAGE/volumes.csv" not in names2
            profile2 = z.read("PC_Context_Pack/01_PC_PROFILE/system_profile.json").decode("utf-8-sig")
            assert "Selected App" not in profile2 and "Drive" not in profile2
            assert counts2["files"] == 0 and counts2["software"] == 0 and counts2["drives"] == 0

        # A CIM timeout must fall back to local, read-only Python metadata and not abort.
        original_runner = run_powershell_json
        try:
            def fake_timeout(*args, **kwargs):
                raise TimeoutError("synthetic CIM timeout")
            globals()["run_powershell_json"] = fake_timeout
            fallback_q = queue.Queue()
            create_scan_payload(fallback_q, threading.Event(), [])
            fallback_payloads = [item[1] for item in list(fallback_q.queue) if item[0] == "done"]
            assert len(fallback_payloads) == 1
            assert any("python_fallback_used" in w.get("Reason", "") for w in fallback_payloads[0]["scan_warnings"])
        finally:
            globals()["run_powershell_json"] = original_runner

    # Product-name consistency guard: the GUI and launcher use one shared constant.
    assert APP_NAME == "PC Context Builder"
    launcher_source = Path(__file__).with_name("start.bat").read_text(encoding="utf-8")
    assert "from app_config import APP_NAME; print(APP_NAME)" in launcher_source
    assert "Starting %APP_NAME%..." in launcher_source
    assert "%APP_NAME% exited with an error." in launcher_source
    assert "AI PC Intelligence" not in launcher_source

    # Regression guard for Tkinter geometry-manager parent consistency.
    source = Path(__file__).read_text(encoding="utf-8")
    overview_source = inspect.getsource(ReviewWindow._build_overview_tab)
    assert "values=(self.t(label), value)" in overview_source
    app_build_source = inspect.getsource(App._build)
    assert '"• " + self.t(line)' in app_build_source
    files_tab = source.split("    def _build_files_tab(self):", 1)[1].split("    def _visible_folder_rows(self):", 1)[0]
    assert "file_table = ttk.Frame(f)" in files_tab
    assert "self.file_tree = ttk.Treeview(file_table," in files_tab
    assert "ttk.Scrollbar(file_table," in files_tab
    assert "self.file_tree.grid(row=0, column=0" in files_tab
    assert "file_vscroll.grid(row=0, column=1" in files_tab
    assert "file_hscroll.grid(row=1, column=0" in files_tab
    assert "self.file_tree = ttk.Treeview(f," not in files_tab
    ps_runner_source = inspect.getsource(run_powershell_json)
    assert "_communicate_with_timeout(proc" in ps_runner_source
    assert "proc.poll() is None" not in ps_runner_source
    communicate_source = inspect.getsource(_communicate_with_timeout)
    assert "proc.communicate(timeout=" in communicate_source
    memory_source = inspect.getsource(get_physical_memory_bytes)
    assert "GlobalMemoryStatusEx" in memory_source
    assert "motherboard_manufacturer" in inspect.getsource(normalize_system_result)

    print("SELF-TEST PASS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not is_windows():
        print(tr("Windows 11 only", load_language_preference()))
        return
    root = Tk()
    try:
        style = ttk.Style(root)
        for theme in ("vista", "xpnative", "clam"):
            try:
                style.theme_use(theme); break
            except Exception:
                continue
    except Exception:
        pass
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
