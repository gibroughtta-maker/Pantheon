"""NVIDIA NIM gateway adapter.

NIM (NVIDIA Inference Microservices) speaks the OpenAI chat completions
wire format. The default base URL is the NIM cloud endpoint; for self-
hosted NIM you pass your own ``base_url``.

NIM is the v0.3 plan's preferred backend for Chinese-language personas
(Qwen, Kimi, GLM, MiniMax) — see plan §2.3.

Default models (M1; expand as community contributes):

  - nim/qwen2-72b-instruct
  - nim/kimi-k2
  - nim/glm-4-9b
  - nim/minimax-abab-7
"""
from __future__ import annotations

import os

from pantheon.gateway.openai_compat import OpenAICompatibleGateway
from pantheon.gateway.rate_limit import RateLimiter

DEFAULT_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NimGateway(OpenAICompatibleGateway):
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        timeout: float = 60.0,
        model_allowlist: list[str] | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url or os.environ.get("NIM_BASE_URL", DEFAULT_NIM_BASE_URL),
            api_key=api_key or os.environ.get("NIM_API_KEY"),
            timeout=timeout,
            default_headers={"Accept": "application/json"},
            model_allowlist=model_allowlist,
            rate_limiter=rate_limiter,
        )
