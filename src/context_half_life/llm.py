"""Thin chat wrapper with deterministic decoding, timing and model-digest capture.

Local models run through Ollama. Hosted adapters read keys from the environment only.
"""
import hashlib
import json
import os
import time
from dataclasses import dataclass, field

from . import SEED


@dataclass
class Reply:
    text: str
    prompt_tokens: int
    completion_tokens: int
    wall_s: float
    prefill_s: float = 0.0
    decode_s: float = 0.0
    model: str = ""
    extra: dict = field(default_factory=dict)


def prompt_hash(messages) -> str:
    return hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()[:16]


def _gpu_temp():
    import subprocess
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout.split()[0]
        return int(out)
    except Exception:  # noqa: BLE001
        return 0


class OllamaChat:
    """Chat against a local Ollama server (temperature 0, fixed seed, explicit context size)."""

    def __init__(self, model, num_ctx=32768, num_predict=128, seed=SEED, host=None):
        import ollama
        self.model, self.num_ctx, self.num_predict, self.seed = model, num_ctx, num_predict, seed
        self.client = ollama.Client(host=host or os.environ.get("OLLAMA_HOST"))

    def digest(self) -> str:
        info = self.client.list()
        for m in info["models"]:
            name = m.get("model") or m.get("name")
            if name == self.model or name == self.model + ":latest":
                return m.get("digest", "")
        return ""

    def _throttle(self):
        """Be gentle with the GPU: short pause after every call, longer pause when it runs hot."""
        self._calls = getattr(self, "_calls", 0) + 1
        time.sleep(float(os.environ.get("CHR_COOLDOWN_S", "0.15")))
        if self._calls % 25 == 0:
            limit = int(os.environ.get("CHR_MAX_GPU_TEMP", "78"))
            while _gpu_temp() > limit:
                time.sleep(15)

    def chat(self, messages, num_predict=None, seed=None) -> Reply:
        self._throttle()
        t0 = time.perf_counter()
        r = self.client.chat(
            model=self.model, messages=messages, keep_alive="30m",
            options={"temperature": 0.0, "seed": self.seed if seed is None else seed,
                     "num_ctx": self.num_ctx, "num_predict": num_predict or self.num_predict})
        wall = time.perf_counter() - t0
        return Reply(
            text=r["message"]["content"], prompt_tokens=r.get("prompt_eval_count", 0),
            completion_tokens=r.get("eval_count", 0), wall_s=wall,
            prefill_s=r.get("prompt_eval_duration", 0) / 1e9, decode_s=r.get("eval_duration", 0) / 1e9,
            model=self.model)


def hosted_key(name: str) -> str:
    """API keys come only from environment variables."""
    key = os.environ.get(name, "")
    if not key:
        raise RuntimeError(f"set {name} in the environment to use this hosted model")
    return key
