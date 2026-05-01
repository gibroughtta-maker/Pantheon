"""Agent — a debate seat. Holds (persona, model, working_memory).

Swap operations mutate the agent's pointers but PRESERVE conversation history.
This is what lets a new persona "inherit" the transcript and open with a
handoff statement (relay mode).

Swaps are intended to be applied at phase boundaries by the Pantheon
coordinator. Calling them mid-phase is allowed but not recommended; the
coordinator's `queue_swap*` API enforces the boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pantheon.core.model import Model
from pantheon.core.persona import Persona
from pantheon.gateway.base import CallResult
from pantheon.memory.episodic import EpisodicStore, NullEpisodicStore
from pantheon.memory.working import Message, WorkingMemory


@dataclass
class Agent:
    seat: int
    persona: Persona
    model: Model
    instance_suffix: str = ""  # for multi-instance e.g. confucius#1 / confucius#2

    memory: WorkingMemory = field(init=False)
    episodic: EpisodicStore = field(default_factory=NullEpisodicStore)

    swap_log: list[tuple[str, str, str]] = field(default_factory=list)
    # entries: (kind, from_id, to_id) where kind ∈ {"persona","model","memory"}

    # When a persona swap is applied, the framework sets this to a handoff
    # statement. The next `speak()` consumes it (auto-prepending and clearing).
    pending_handoff: str = ""

    def __post_init__(self) -> None:
        self.memory = WorkingMemory(seat=self.seat)

    @property
    def label(self) -> str:
        suffix = f"#{self.instance_suffix}" if self.instance_suffix else ""
        return f"{self.persona.id}{suffix}"

    def wear(self, persona: Persona, *, instance_suffix: str = "") -> None:
        """Replace persona without touching history. The persona will see all
        prior messages on its next call and is expected to begin with a
        handoff statement (composed by `relay.compose_handoff`)."""
        prev = self.label
        self.persona = persona
        self.instance_suffix = instance_suffix
        self.swap_log.append(("persona", prev, self.label))

    def swap_persona(self, persona: Persona, *, instance_suffix: str = "") -> None:
        self.wear(persona, instance_suffix=instance_suffix)

    def swap_model(self, model: Model) -> None:
        prev = self.model.id
        self.model = model
        self.swap_log.append(("model", prev, model.id))

    def swap_memory(self, episodic: EpisodicStore) -> None:
        self.episodic = episodic
        self.swap_log.append(("memory", "<prev>", "<new>"))

    async def speak(
        self,
        prompt: str,
        *,
        phase: str,
        prefix: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        seed: int | None = None,
    ) -> CallResult:
        """Append the prompt as a user turn, call the LLM, append the reply
        as an assistant turn. `prefix` is forced into the start of the reply
        (used for handoff statements). If `pending_handoff` is set on this
        agent, it is consumed as the prefix (and cleared) when no explicit
        prefix is provided."""
        if not prefix and self.pending_handoff:
            prefix = self.pending_handoff
            self.pending_handoff = ""
        self.memory.append(Message(role="user", content=prompt, phase=phase))
        sysprompt = self.persona.system_prompt(instance_suffix=self.instance_suffix)
        messages = self.memory.render_for_llm(sysprompt)
        if prefix:
            messages.append({"role": "assistant", "content": prefix})
        result = await self.model.call(
            messages, temperature=temperature, max_tokens=max_tokens, seed=seed
        )
        text = (prefix + result.text) if prefix else result.text
        self.memory.append(
            Message(role="assistant", content=text, persona_id=self.persona.id, phase=phase)
        )
        return CallResult(
            text=text,
            model_id=result.model_id,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
            raw=result.raw,
        )
