"""Topic classification — turn a user's question into a 7-dim topic vector.

Three strategies fused (plan §5.2):

  ① user-supplied tags      weight 1.0   highest priority
  ② embedding similarity     weight 0.6   default; zero LLM cost
  ③ small-LLM zero-shot      weight 0.4   optional; needs a Gateway

The vector matches the 7 dimensions used by `pantheon.calibration.probes`
(ethics / governance / education / business / technology / divination /
emotion). This lets the persona-skill cosine in `compute_weights` match
on the same axis without a translation layer.
"""
from pantheon.topic.classifier import (
    TopicClassifier,
    classify_topic,
    classify_topic_embedding,
    classify_topic_llm,
)

__all__ = [
    "TopicClassifier",
    "classify_topic",
    "classify_topic_embedding",
    "classify_topic_llm",
]
