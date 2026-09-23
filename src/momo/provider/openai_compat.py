"""OpenAI-compatible HTTP provider (optional; needs API key)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from momo.provider.base import ModelProvider


class OpenAICompatibleProvider(ModelProvider):
    """Thin client using stdlib + optional httpx; reads OPENAI_* env."""

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or ""
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
        self.timeout = timeout

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY 未设置；请配置环境变量或改用 MOMO_PROVIDER=demo"
            )
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps(
            {"model": self.model, "messages": messages, "temperature": 0.2}
        ).encode("utf-8")
        url = f"{self.base_url}/chat/completions"
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"OpenAI HTTP {exc.code}: {detail}") from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"OpenAI 请求失败: {exc}") from exc

        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI 返回空 choices")
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if not content:
            raise RuntimeError("OpenAI 返回空 content")
        return str(content)
