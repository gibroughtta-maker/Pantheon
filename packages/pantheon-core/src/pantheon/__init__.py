"""Pantheon — multi-agent debate framework. See README and the v0.3 plan."""
from pantheon.core.agent import Agent
from pantheon.core.model import Model
from pantheon.core.pantheon import Pantheon, quick_debate
from pantheon.core.persona import Persona, load_persona, load_personas_dir, registry
from pantheon.core.weights import compute_weights
from pantheon.gateway.base import CallResult, Gateway, GatewayError
from pantheon.gateway.mock import MockGateway, ScriptedReply
from pantheon.gateway.nim import NimGateway
from pantheon.gateway.openai_compat import OpenAICompatibleGateway
from pantheon.gateway.openclaw import OpenClawGateway
from pantheon.gateway.rate_limit import RateLimiter, default_rate_limiter
from pantheon.gateway.replay import ReplayGateway
from pantheon.memory.sqlite_episodic import SqliteEpisodicStore
from pantheon.obs.budget import BudgetExceeded, BudgetGuard
from pantheon.types.persona import PersonaSpec
from pantheon.types.verdict import Verdict

__version__ = "0.1.0a0"

__all__ = [
    "Agent",
    "BudgetExceeded",
    "BudgetGuard",
    "CallResult",
    "Gateway",
    "GatewayError",
    "MockGateway",
    "Model",
    "NimGateway",
    "OpenAICompatibleGateway",
    "OpenClawGateway",
    "Pantheon",
    "Persona",
    "PersonaSpec",
    "RateLimiter",
    "ReplayGateway",
    "ScriptedReply",
    "SqliteEpisodicStore",
    "Verdict",
    "default_rate_limiter",
    "compute_weights",
    "load_persona",
    "load_personas_dir",
    "quick_debate",
    "registry",
    "__version__",
]
