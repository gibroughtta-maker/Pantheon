"""TopicClassifier — three-strategy fusion (tags + embedding + LLM)."""
from __future__ import annotations

import json

import pytest

from pantheon import Model, MockGateway, ScriptedReply
from pantheon.calibration.probes import DIMENSIONS
from pantheon.topic import (
    TopicClassifier,
    classify_topic,
    classify_topic_embedding,
    classify_topic_llm,
)


def test_embedding_classifier_returns_all_dims():
    v = classify_topic_embedding("Should I take this job offer?")
    assert set(v.keys()) == set(DIMENSIONS)
    for s in v.values():
        assert 0.0 <= s <= 1.0


@pytest.mark.asyncio
async def test_user_tags_passthrough_dominates():
    """If the user supplies tags, the fused output should heavily reflect them
    (weight 1.0 vs embedding 0.6)."""
    cls = TopicClassifier()
    v = await cls.classify(
        "anything", user_tags={"business": 1.0, "ethics": 0.5}
    )
    # business and ethics should be the top two
    ranked = sorted(v.items(), key=lambda x: -x[1])
    top2 = {k for k, _ in ranked[:2]}
    assert "business" in top2


@pytest.mark.asyncio
async def test_classify_topic_helper():
    v = await classify_topic("Should friends always forgive each other?",
                              user_tags={"ethics": 1.0})
    assert v["ethics"] == 1.0  # min-max normalize → top-tagged dim → 1.0


@pytest.mark.asyncio
async def test_llm_classifier_parses_json():
    gw = MockGateway()
    payload = json.dumps({d: 0.5 if d == "ethics" else 0.0 for d in DIMENSIONS})
    gw.add_reply(ScriptedReply(text=f"```\n{payload}\n```", model_id="judge"))
    judge = Model(id="judge", gateway=gw)
    v = await classify_topic_llm("Q?", judge)
    assert v["ethics"] == 0.5
    assert v["business"] == 0.0


@pytest.mark.asyncio
async def test_llm_classifier_falls_back_on_garbage():
    gw = MockGateway()
    gw.add_reply(ScriptedReply(text="This is not JSON, sorry.", model_id="judge"))
    judge = Model(id="judge", gateway=gw)
    v = await classify_topic_llm("Q?", judge)
    # Falls back to all-zero rather than raising.
    assert v == {d: 0.0 for d in DIMENSIONS}


@pytest.mark.asyncio
async def test_breakdown_records_all_three_strategies():
    gw = MockGateway()
    payload = json.dumps({d: (1.0 if d == "education" else 0.0) for d in DIMENSIONS})
    gw.add_reply(ScriptedReply(text=payload, model_id="judge"))
    judge = Model(id="judge", gateway=gw)
    cls = TopicClassifier(llm_judge=judge)
    await cls.classify("How do you teach courage?", user_tags={"ethics": 0.3})
    breakdown = cls.last_breakdown()
    assert "tags" in breakdown
    assert "embedding" in breakdown
    assert "llm" in breakdown
    assert breakdown["tags"]["ethics"] == 0.3
    assert breakdown["llm"]["education"] == 1.0


@pytest.mark.asyncio
async def test_no_user_tags_no_llm_falls_back_to_embedding_only():
    cls = TopicClassifier()  # no llm
    v = await cls.classify("anything")
    # vector still well-formed
    assert set(v.keys()) == set(DIMENSIONS)
    # tags branch is zero
    assert all(x == 0.0 for x in cls.last_breakdown()["tags"].values())
    # llm branch is zero
    assert all(x == 0.0 for x in cls.last_breakdown()["llm"].values())
