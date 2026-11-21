"""Synthetic-only PC Context Builder filesystem performance baseline.

Writes temporary test files only; does not inspect real user directories.
Does not impose hardware-dependent speed thresholds.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


def benchmark(n: int) -> dict:
    if not 10 <= n <= 20000:
        raise ValueError("--files must be between 10 and 20000")
    with tempfile.TemporaryDirectory(prefix="pc-context-perf-") as td:
        root = Path(td) / "sample"
        root.mkdir()
        for i in range(n):
            folder = root / f"section_{i // 200:03}"
            folder.mkdir(exist_ok=True)
            (folder / f"日本語_{i:05}.txt").write_bytes(bytes((i % 256,)) * 128)
        q = queue.Queue()
        tracemalloc.start()
        before = time.perf_counter()
        main.scan_filesystem([str(root)], q, threading.Event())
        elapsed = time.perf_counter() - before
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        done = [value for kind, value in list(q.queue) if kind == "filesystem_done"]
        if len(done) != 1 or done[0]["counts"]["files"] != n:
            raise AssertionError("Synthetic filesystem baseline lost indexed files")
        return {
            "version": main.VERSION,
            "synthetic_files": n,
            "synthetic_folders": done[0]["counts"]["folders"],
            "elapsed_seconds": round(elapsed, 3),
            "files_per_second": round(n / max(elapsed, 0.0001), 3),
            "python_tracemalloc_peak_bytes": peak,
            "status": done[0]["status"],
            "note": "Only Python-tracked memory is counted; compare on same hardware.",
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", type=int, default=4000)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    result = benchmark(args.files)
    Path(args.report).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
