"""Conservative recovery of orphaned, unpublished context ZIP staging files.

A small JSON journal records only a random staging basename and file identity.
Unverified or recently active staging files are never deleted automatically.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import time
import uuid

_PREFIX = ".PC_Context_Txn_"
_SUFFIX = ".json"
_TMP_PREFIX = ".PC_Context_Pack_"


def _sync_directory(folder: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(str(folder), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def begin(output_dir: str, temporary: str) -> Path:
    """Create a journal bound to the exact temporary ZIP file identity."""
    folder = Path(output_dir)
    tmp = Path(temporary)
    if tmp.parent.resolve() != folder.resolve() or not tmp.name.startswith(_TMP_PREFIX) or not tmp.name.endswith(".tmp"):
        raise ValueError("Invalid temporary ZIP path")
    st = os.stat(tmp, follow_symlinks=False)
    if not stat.S_ISREG(st.st_mode) or st.st_ino == 0:
        raise ValueError("Filesystem cannot prove temporary ZIP identity")
    record = {
        "version": 1,
        "temporary_name": tmp.name,
        "device": st.st_dev,
        "inode": st.st_ino,
        "created": time.time(),
    }
    journal = folder / (_PREFIX + uuid.uuid4().hex + _SUFFIX)
    fd = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=True)
            stream.flush()
            os.fsync(stream.fileno())
        _sync_directory(folder)
    except BaseException:
        try:
            journal.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return journal


def finish(journal: Path | None) -> None:
    if journal is not None:
        journal.unlink(missing_ok=True)


def _trusted_pair(folder: Path, journal: Path, now: float, min_age: int):
    if journal.is_symlink() or not journal.is_file():
        return None
    if now - journal.stat().st_mtime < min_age:
        return None
    try:
        if journal.stat().st_size > 2048:
            return None
        data = json.loads(journal.read_text(encoding="utf-8"))
        name = data.get("temporary_name")
        if (data.get("version") != 1 or not isinstance(name, str)
                or not name.startswith(_TMP_PREFIX) or not name.endswith(".tmp")
                or Path(name).name != name or "/" in name or "\\" in name):
            return None
        temp = folder / name
        st = os.stat(temp, follow_symlinks=False)
        if not stat.S_ISREG(st.st_mode) or st.st_ino == 0:
            return None
        if st.st_dev != data.get("device") or st.st_ino != data.get("inode"):
            return None
        if now - float(data["created"]) < min_age:
            return None
        return temp
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def discover_stale(output_dir: str, min_age_seconds: int = 3600) -> list[str]:
    """Return only verified candidates; no mutation occurs."""
    folder = Path(output_dir)
    result = []
    for journal in folder.glob(_PREFIX + "*" + _SUFFIX):
        temp = _trusted_pair(folder, journal, time.time(), min_age_seconds)
        if temp is not None:
            result.append(temp.name)
    return sorted(result)


def cleanup_confirmed(output_dir: str, min_age_seconds: int = 3600) -> int:
    """Only call after explicit user confirmation; recheck identity at deletion."""
    folder = Path(output_dir)
    deleted = 0
    for journal in folder.glob(_PREFIX + "*" + _SUFFIX):
        temp = _trusted_pair(folder, journal, time.time(), min_age_seconds)
        if temp is None:
            continue
        # Do not follow symlinks or remove arbitrary replacement files.
        check = _trusted_pair(folder, journal, time.time(), min_age_seconds)
        if check != temp:
            continue
        temp.unlink()
        journal.unlink(missing_ok=True)
        deleted += 1
    return deleted
