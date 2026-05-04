"""OpenClaw gateway adapter.

OpenClaw (the user's existing multi-LLM router) speaks the OpenAI chat
completions wire format with two additions:

  1. A ``X-OpenClaw-Project`` header that scopes calls to a project's
     budget pool and audit log.
  2. An optional ``X-OpenClaw-Persona`` header which lets OpenClaw
     route to a model affinity-tuned for that persona's language and
     domain.

Both headers are best-effort hints; if the OpenClaw deployment doesn't
recognize them, the call still succeeds via the OpenAI-compat path.

Usage:

    from pantheon.gateway import OpenClawGateway
    gw = OpenClawGateway(
        base_url="https://openclaw.example.com/v1",
        api_key=os.environ["OPENCLAW_API_KEY"],
        project="pantheon-prod",
    )
"""
from __future__ import annotations

from pantheon.gateway.openai_compat import OpenAICompatibleGateway
from pantheon.gateway.rate_limit import RateLimiter


class OpenClawGateway(OpenAICompatibleGateway):
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        *,
        project: str | None = None,
        timeout: float = 60.0,
        model_allowlist: list[str] | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        headers: dict[str, str] = {}
        if project:
            headers["X-OpenClaw-Project"] = project
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            default_headers=headers,
            model_allowlist=model_allowlist,
            rate_limiter=rate_limiter,
        )
        self._project = project

    async def call(self, model_id, messages, **kw):
        # If a system message contains a [persona:<id>] marker (the same
        # convention MockGateway uses for routing), forward the persona
        # hint to OpenClaw.
        persona_id = self._sniff_persona(messages)
        if persona_id is not None:
            self._headers = {**self._headers, "X-OpenClaw-Persona": persona_id}
        return await super().call(model_id, messages, **kw)

    @staticmethod
    def _sniff_persona(messages: list[dict[str, str]]) -> str | None:
        for m in messages:
            if m["role"] != "system":
                continue
            content = m["content"]
            i = content.find("[persona:")
            if i < 0:
                continue
            j = content.find("]", i)
            if j > i:
                return content[i + len("[persona:") : j]
        return None
