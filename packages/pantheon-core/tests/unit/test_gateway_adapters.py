"""OpenClawGateway and NimGateway thin-shell adapters."""
from __future__ import annotations

from pantheon.gateway import NimGateway, OpenClawGateway


def test_openclaw_sets_project_header():
    gw = OpenClawGateway(
        base_url="http://example/v1",
        api_key="k",
        project="pantheon-prod",
    )
    assert gw._headers.get("X-OpenClaw-Project") == "pantheon-prod"


def test_openclaw_sniffs_persona_marker():
    msgs = [
        {"role": "system", "content": "[persona:confucius]\nyou are confucius"},
        {"role": "user", "content": "speak"},
    ]
    assert OpenClawGateway._sniff_persona(msgs) == "confucius"


def test_openclaw_no_persona_marker():
    msgs = [{"role": "system", "content": "no marker here"}]
    assert OpenClawGateway._sniff_persona(msgs) is None


def test_nim_default_base_url(monkeypatch):
    monkeypatch.delenv("NIM_BASE_URL", raising=False)
    monkeypatch.delenv("NIM_API_KEY", raising=False)
    gw = NimGateway()
    assert "nvidia.com" in gw._base_url
    assert gw._api_key is None


def test_nim_respects_env(monkeypatch):
    monkeypatch.setenv("NIM_BASE_URL", "https://my-nim/v1")
    monkeypatch.setenv("NIM_API_KEY", "secret")
    gw = NimGateway()
    assert gw._base_url == "https://my-nim/v1"
    assert gw._api_key == "secret"


def test_nim_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("NIM_BASE_URL", "https://env-nim/v1")
    gw = NimGateway(base_url="https://override/v1", api_key="k")
    assert gw._base_url == "https://override/v1"


def test_nim_allowlist_enforced():
    gw = NimGateway(api_key="k", model_allowlist=["nim/qwen2-72b"])
    assert gw.supports("nim/qwen2-72b")
    assert not gw.supports("gpt-4o")
