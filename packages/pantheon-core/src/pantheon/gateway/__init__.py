"""LLM gateway abstraction.

A `Gateway` resolves a model id (e.g. ``claude-opus-4-7``) to an actual
provider. Pantheon never embeds provider-specific logic outside this package;
swap models freely.
"""
from pantheon.gateway.base import CallResult, Gateway, GatewayError
from pantheon.gateway.mock import MockGateway, ScriptedReply
from pantheon.gateway.nim import NimGateway
from pantheon.gateway.openai_compat import OpenAICompatibleGateway
from pantheon.gateway.openclaw import OpenClawGateway
from pantheon.gateway.rate_limit import RateLimiter, default_rate_limiter
from pantheon.gateway.replay import ReplayGateway

__all__ = [
    "CallResult",
    "Gateway",
    "GatewayError",
    "MockGateway",
    "NimGateway",
    "OpenAICompatibleGateway",
    "OpenClawGateway",
    "RateLimiter",
    "ReplayGateway",
    "ScriptedReply",
    "default_rate_limiter",
]
