"""LLM gateway abstraction.

A `Gateway` resolves a model id (e.g. ``claude-opus-4-7``) to an actual
provider. Pantheon never embeds provider-specific logic outside this package;
swap models freely.
"""
from pantheon.gateway.base import CallResult, Gateway, GatewayError
from pantheon.gateway.mock import MockGateway, ScriptedReply
from pantheon.gateway.openai_compat import OpenAICompatibleGateway
from pantheon.gateway.replay import ReplayGateway

__all__ = [
    "CallResult",
    "Gateway",
    "GatewayError",
    "MockGateway",
    "OpenAICompatibleGateway",
    "ReplayGateway",
    "ScriptedReply",
]
