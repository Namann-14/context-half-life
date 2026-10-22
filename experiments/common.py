"""Shared helpers for experiment scripts: resumable JSONL logging and environment capture."""
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
RAW = ROOT / "results" / "raw"
SUMMARY = ROOT / "results" / "summary"
ENV = ROOT / "results" / "env"


class JsonlLog:
    """Append-only JSONL log keyed by a unique `key` field; re-running skips finished keys."""

    def __init__(self, name):
        RAW.mkdir(parents=True, exist_ok=True)
        self.path = RAW / f"{name}.jsonl"
        self.done = set()
        if self.path.exists():
            for line in self.path.read_text(encoding="utf8").splitlines():
                if line.strip():
                    self.done.add(json.loads(line)["key"])

    def __contains__(self, key):
        return key in self.done

    def write(self, rec):
        with self.path.open("a", encoding="utf8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.done.add(rec["key"])


def read_jsonl(name):
    p = RAW / f"{name}.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf8").splitlines() if x.strip()] if p.exists() else []


def capture_env(models=()):
    """Write results/env/environment.json: versions, hardware and model digests."""
    ENV.mkdir(parents=True, exist_ok=True)
    info = dict(python=sys.version, platform=platform.platform())
    for cmd, key in ((["ollama", "--version"], "ollama"),
                     (["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"], "gpu")):
        try:
            info[key] = subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception as e:  # noqa: BLE001
            info[key] = f"unavailable: {e}"
    info["models"] = dict(models)
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
    (ENV / "pip_freeze.txt").write_text(freeze, encoding="utf8")
    (ENV / "environment.json").write_text(json.dumps(info, indent=2), encoding="utf8")
    return info
