"""System roles — Moderator, Oracle, Auditor.

These do not occupy a debate seat. They are framework-internal agents that
shepherd the FSM, render the verdict, and audit citations.
"""
from pantheon.roles.auditor import Auditor
from pantheon.roles.moderator import Moderator
from pantheon.roles.oracle import Oracle

__all__ = ["Auditor", "Moderator", "Oracle"]
