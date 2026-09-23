"""Ollama local provider stub / thin client."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from momo.provider.base import ModelProvider


class OllamaProvider(ModelProvider):
    """Calls Ollama ``/api/generate``. Defaults to localhost."""

    name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("OLLAMA_BASE_URL")
            or "http://127.0.0.1:11434"
        ).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL") or "llama3.2"
        self.timeout = timeout

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        full_prompt = prompt
        if system:
            full_prompt = f"{system.rstrip()}\n\n{prompt}"
        body = json.dumps(
            {"model": self.model, "prompt": full_prompt, "stream": False}
        ).encode("utf-8")
        url = f"{self.base_url}/api/generate"
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Ollama 不可达 ({self.base_url}): {exc}；"
                "可改用 MOMO_PROVIDER=demo"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Ollama 请求失败: {exc}") from exc

        text = payload.get("response")
        if text is None:
            raise RuntimeError("Ollama 返回空 response")
        return str(text)
