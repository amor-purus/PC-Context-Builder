#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FlClash / Mihomo local log collector. Requires websocket-client."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = APP_DIR / "settings.json"
DEFAULT_SETTINGS = {
    "controller": "http://127.0.0.1:9090",
    "secret": "",
    "connection_interval_ms": 250,
    "connection_snapshot_seconds": 5,
    "log_level": "debug",
    "context_refresh_seconds": 60,
    "output_dir": "FlClashLogs"
}


def local_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def write_default_settings() -> None:
    SETTINGS_FILE.write_text(
        json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )


def load_settings() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        write_default_settings()
        print(f"已创建配置文件：{SETTINGS_FILE}")
        print("如 FlClash API 设置了密钥，请先把密钥填入 settings.json 的 secret 字段。\n")
    try:
        settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise RuntimeError(f"读取 settings.json 失败：{exc}") from exc
    if not isinstance(settings, dict):
        raise RuntimeError("settings.json 顶层必须是 JSON 对象。")
    merged = dict(DEFAULT_SETTINGS)
    merged.update(settings)
    merged["controller"] = str(merged["controller"]).rstrip("/")
    if not merged["controller"].startswith(("http://", "https://")):
        raise RuntimeError("controller 必须以 http:// 或 https:// 开头。")
    merged["connection_interval_ms"] = max(100, min(5000, int(merged["connection_interval_ms"])))
    merged["connection_snapshot_seconds"] = max(1, int(merged["connection_snapshot_seconds"]))
    merged["context_refresh_seconds"] = max(10, int(merged["context_refresh_seconds"]))
    merged["log_level"] = str(merged["log_level"]).lower()
    if merged["log_level"] not in {"debug", "info", "warning", "error"}:
        merged["log_level"] = "debug"
    return merged


class JsonlWriter:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def emit(self, event: str, data: Any, source: str = "collector") -> None:
        now = datetime.now().astimezone()
        record = {
            "received_at": now.isoformat(timespec="milliseconds"),
            "source": source,
            "event": event,
            "data": data
        }
        target = self.output_dir / f"{now:%Y-%m-%d}.jsonl"
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=str)
        with self.lock:
            with target.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(line + "\n")


class ApiClient:
    def __init__(self, base: str, secret: str):
        self.base = base
        self.secret = secret.strip()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "FlClash-Log-Collector/1.0"}
        if self.secret:
            headers["Authorization"] = f"Bearer {self.secret}"
        return headers

    def get_json(self, path: str, timeout: int = 8) -> Any:
        req = urllib.request.Request(self.base + path, headers=self._headers(), method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}

    def websocket_url(self, path: str) -> str:
        parsed = urllib.parse.urlsplit(self.base)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        return urllib.parse.urlunsplit((scheme, parsed.netloc, path.split("?", 1)[0],
                                        path.split("?", 1)[1] if "?" in path else "", ""))

    def websocket_headers(self) -> list[str]:
        return [f"Authorization: Bearer {self.secret}"] if self.secret else []


def load_websocket_module():
    try:
        import websocket  # type: ignore
        return websocket
    except ImportError as exc:
        raise RuntimeError(
            "缺少 websocket-client 依赖。请双击 run.bat 自动安装；或执行：py -3 -m pip install --user websocket-client"
        ) from exc


class ConnectionTracker:
    """Writes connection-open, periodic changed snapshots, and connection-close events."""
    def __init__(self, writer: JsonlWriter, snapshot_seconds: int):
        self.writer = writer
        self.snapshot_seconds = snapshot_seconds
        self.active: dict[str, dict[str, Any]] = {}
        self.last_saved: dict[str, dict[str, Any]] = {}
        self.last_saved_at: dict[str, float] = {}
        self.last_totals_at = 0.0
        self.last_totals_value: dict[str, Any] | None = None

    @staticmethod
    def stable_part(conn: dict[str, Any]) -> str:
        subset = {k: conn.get(k) for k in ("metadata", "chains", "providerChains", "rule", "rulePayload")}
        return json.dumps(subset, ensure_ascii=False, sort_keys=True, default=str)

    @staticmethod
    def byte_pair(conn: dict[str, Any]) -> tuple[Any, Any]:
        return conn.get("upload"), conn.get("download")

    def process(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            self.writer.emit("connections_unexpected_payload", {"payload": payload}, "connections")
            return
        rows = payload.get("connections", [])
        if not isinstance(rows, list):
            return

        now = time.monotonic()
        current_ids: set[str] = set()
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            cid = str(raw.get("id") or "")
            if not cid:
                # Preserve malformed entries instead of silently dropping them.
                self.writer.emit("connection_unidentified", raw, "connections")
                continue
            current_ids.add(cid)
            previous = self.active.get(cid)
            if previous is None:
                self.writer.emit("connection_open", raw, "connections")
                self.last_saved[cid] = raw
                self.last_saved_at[cid] = now
            else:
                saved = self.last_saved.get(cid, previous)
                critical_changed = self.stable_part(raw) != self.stable_part(saved)
                bytes_changed = self.byte_pair(raw) != self.byte_pair(saved)
                due = now - self.last_saved_at.get(cid, now) >= self.snapshot_seconds
                if critical_changed or (bytes_changed and due):
                    self.writer.emit("connection_update", raw, "connections")
                    self.last_saved[cid] = raw
                    self.last_saved_at[cid] = now
            self.active[cid] = raw

        for cid in list(self.active.keys() - current_ids):
            last = self.active.pop(cid)
            self.writer.emit("connection_closed", last, "connections")
            self.last_saved.pop(cid, None)
            self.last_saved_at.pop(cid, None)

        # Keep aggregate counters too; useful for correlating a quiet connection list.
        totals = {k: payload.get(k) for k in ("uploadTotal", "downloadTotal", "memory") if k in payload}
        if totals and (now - self.last_totals_at >= 10 or totals != self.last_totals_value):
            # Aggregate totals can change on every WS tick; cap these records to one per 10 seconds.
            if now - self.last_totals_at >= 10:
                self.writer.emit("connection_totals", totals, "connections")
                self.last_totals_at = now
                self.last_totals_value = totals


class Collector:
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings
        output = Path(settings["output_dir"])
        if not output.is_absolute():
            output = APP_DIR / output
        self.writer = JsonlWriter(output)
        self.api = ApiClient(settings["controller"], settings["secret"])
        self.tracker = ConnectionTracker(self.writer, settings["connection_snapshot_seconds"])
        self.stop_event = threading.Event()
        self.context_hashes: dict[str, str] = {}

    def say(self, message: str) -> None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)

    def startup_check(self) -> None:
        try:
            version = self.api.get_json("/version")
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                secret_len = len(str(self.settings.get("secret", "")).strip())
                raise RuntimeError(
                    "API 返回 401（认证未通过）。\n"
                    f"当前采集器读取的密钥长度：{secret_len} 个字符（不会显示密钥内容）。\n"
                    "请确认本目录 settings.json 是本次压缩包内的新文件，并且 secret 与 FlClash「外部控制器密钥」完全一致。\n"
                    "注意：不要把密钥发到聊天或截图中。"
                ) from exc
            raise RuntimeError(f"API 返回 HTTP {exc.code}。请确认 External Controller 已启用且端口正确。") from exc
        except Exception as exc:
            raise RuntimeError(
                f"无法连接 {self.settings['controller']}：{exc}\n"
                "请在 FlClash 中启用 External Controller（外部控制器），并确认监听地址为 127.0.0.1:9090。"
            ) from exc
        self.writer.emit("core_version", version, "api")
        self.say(f"已连接 Mihomo API：{version.get('version', '版本未知')}")

    def snapshot_context(self) -> None:
        # Deliberately avoid /configs: it may contain subscription credentials and proxy secrets.
        for endpoint, event in (("/rules", "rules_snapshot"), ("/proxies", "proxies_snapshot")):
            try:
                result = self.api.get_json(endpoint)
                if endpoint == "/proxies" and isinstance(result, dict):
                    all_proxies = result.get("proxies", {})
                    if isinstance(all_proxies, dict):
                        result = {
                            "groups": {
                                name: {k: p.get(k) for k in ("type", "now", "all", "udp") if k in p}
                                for name, p in all_proxies.items()
                                if isinstance(p, dict) and ("now" in p or "all" in p)
                            }
                        }
                digest = hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()
                if self.context_hashes.get(endpoint) != digest:
                    self.context_hashes[endpoint] = digest
                    self.writer.emit(event, result, "api")
            except Exception as exc:
                self.writer.emit("api_snapshot_error", {"endpoint": endpoint, "error": str(exc)}, "api")
                self.say(f"读取 {endpoint} 失败：{exc}")

    def websocket_worker(self, name: str, path: str, on_payload) -> None:
        websocket = load_websocket_module()
        delay = 1
        while not self.stop_event.is_set():
            opened = threading.Event()

            def on_open(ws):
                nonlocal delay
                delay = 1
                opened.set()
                self.writer.emit("websocket_connected", {"endpoint": name}, name)
                self.say(f"{name} 实时流已连接")

            def on_message(ws, message):
                try:
                    payload = json.loads(message)
                    on_payload(payload)
                except Exception as exc:
                    self.writer.emit("websocket_message_error", {
                        "endpoint": name, "error": str(exc), "raw": str(message)[:5000]
                    }, name)

            def on_error(ws, error):
                self.writer.emit("websocket_error", {"endpoint": name, "error": str(error)}, name)
                self.say(f"{name} 连接异常：{error}")

            def on_close(ws, status_code, message):
                self.writer.emit("websocket_disconnected", {
                    "endpoint": name, "status": status_code, "message": str(message or "")
                }, name)

            url = self.api.websocket_url(path)
            app = websocket.WebSocketApp(
                url,
                header=self.api.websocket_headers(),
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            try:
                app.run_forever(ping_interval=20, ping_timeout=10, reconnect=0)
            except Exception as exc:
                self.writer.emit("websocket_worker_exception", {"endpoint": name, "error": str(exc)}, name)
            if not self.stop_event.is_set():
                self.say(f"{name} 将在 {delay} 秒后重连")
                self.stop_event.wait(delay)
                delay = min(delay * 2, 30)

    def context_worker(self) -> None:
        while not self.stop_event.is_set():
            self.snapshot_context()
            self.stop_event.wait(self.settings["context_refresh_seconds"])

    def run(self) -> None:
        self.startup_check()
        self.snapshot_context()
        self.writer.emit("collector_started", {
            "controller": self.settings["controller"],
            "connection_interval_ms": self.settings["connection_interval_ms"],
            "log_level": self.settings["log_level"],
            "note": "本采集器不读取 /configs，避免收集订阅凭据或代理密码。"
        })

        interval = self.settings["connection_interval_ms"]
        log_level = urllib.parse.quote(self.settings["log_level"])
        connections_path = f"/connections?interval={interval}"
        logs_path = f"/logs?level={log_level}&format=structured"

        threads = [
            threading.Thread(target=self.websocket_worker,
                             args=("connections", connections_path, self.tracker.process), daemon=True),
            threading.Thread(target=self.websocket_worker,
                             args=("core_logs", logs_path,
                                   lambda payload: self.writer.emit("core_log", payload, "core_logs")), daemon=True),
            threading.Thread(target=self.context_worker, daemon=True)
        ]
        for thread in threads:
            thread.start()

        output = self.writer.output_dir.resolve()
        self.say("采集已启动。按 Ctrl+C 停止。")
        self.say(f"日志保存目录：{output}")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.say("收到停止指令，正在收尾……")
        finally:
            self.stop_event.set()
            self.writer.emit("collector_stopped", {
                "still_active_connection_count": len(self.tracker.active)
            })
            self.say("采集器已停止。现有日志文件已保存。")


class Tee:
    """Mirror console output to a UTF-8 diagnostic log without hiding it."""
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def main() -> int:
    diagnostic_path = APP_DIR / "collector-startup.log"
    log_file = None
    original_stdout, original_stderr = sys.stdout, sys.stderr
    try:
        log_file = diagnostic_path.open("a", encoding="utf-8", buffering=1)
        sys.stdout = Tee(original_stdout, log_file)
        sys.stderr = Tee(original_stderr, log_file)
        print("\n" + "=" * 68)
        print(f"FlClash 采集器启动时间：{local_iso()}")
        print(f"Python：{sys.version.split()[0]}")
        print(f"诊断日志：{diagnostic_path}")
        settings = load_settings()
        load_websocket_module()
        Collector(settings).run()
        return 0
    except Exception as exc:
        print(f"\n启动失败：{exc}", file=sys.stderr)
        print(f"\n配置文件：{SETTINGS_FILE}", file=sys.stderr)
        print(f"\n详细诊断日志：{diagnostic_path}", file=sys.stderr)
        return 1
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        if log_file is not None:
            log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())