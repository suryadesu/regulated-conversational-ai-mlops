"""Unit and bridged-integration tests for case loading and execution."""

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import provider_stub.main as stub_main
from eval_harness.runner import load_cases, run_case
from gateway.config import Settings
from gateway.main import create_app

CASES_YAML = """
cases:
  - id: sample-contains
    prompt: "What are your business hours?"
    assertions:
      - {type: contains, expected: ["business hours"]}
  - id: sample-judged
    prompt: "Explain a late fee"
    assertions: []
    rubric: "Response is professional."
    repeats: 5
"""


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_load_cases_from_yaml(tmp_path: Path) -> None:
    (tmp_path / "cases.yaml").write_text(CASES_YAML, encoding="utf-8")
    cases = load_cases(tmp_path)
    assert [c.id for c in cases] == ["sample-contains", "sample-judged"]
    assert cases[0].rubric is None and cases[0].assertions
    assert cases[1].rubric is not None and cases[1].repeats == 5


def test_load_real_case_files_parse() -> None:
    cases = load_cases(Path("evals/cases"))
    assert isinstance(cases, list)  # authored content validated end-to-end in test_gate


@pytest.fixture
def bridged_gateway(monkeypatch):
    """Real gateway app whose provider layer talks to the real stub app over ASGI.

    Note: `modA.httpx.AsyncClient` and `modB.httpx.AsyncClient` are the SAME
    module attribute, so a single routing constructor (keyed on base_url)
    replaces it once — separate per-module patches would overwrite each other.
    """
    stub_main._fault_config = stub_main.FaultConfig()
    stub_transport = httpx.ASGITransport(app=stub_main.create_app())
    real_client = httpx.AsyncClient

    def stub_only(*args, **kwargs):
        kwargs["transport"] = stub_transport
        return real_client(*args, **kwargs)

    # Provider client is constructed during lifespan startup: point it at the stub.
    monkeypatch.setattr(httpx, "AsyncClient", stub_only)
    settings = Settings(
        provider="openai_compat",
        provider_base_url="http://stub/v1",
        price_table_path=Path("services/gateway/config/prices.yaml"),
        prompt_dir=Path("prompts"),
    )
    with TestClient(create_app(settings=settings)) as gateway_client:
        gateway_transport = httpx.ASGITransport(app=gateway_client.app)

        def routing(*args, **kwargs):
            base = str(kwargs.get("base_url", ""))
            transport = gateway_transport if base.startswith("http://gateway") else stub_transport
            kwargs["transport"] = transport
            return real_client(*args, **kwargs)

        # Runner/judge clients are constructed per call: route by base_url.
        monkeypatch.setattr(httpx, "AsyncClient", routing)
        yield gateway_client


@pytest.mark.anyio
async def test_run_deterministic_case_passes(bridged_gateway, tmp_path: Path) -> None:
    (tmp_path / "cases.yaml").write_text(CASES_YAML, encoding="utf-8")
    case = load_cases(tmp_path)[0]
    result = await run_case(case, gateway_url="http://gateway", judge_url=None)
    assert result.kind == "deterministic"
    assert result.passed is True
    assert result.votes == []


@pytest.mark.anyio
async def test_run_judged_case_votes_five_times(bridged_gateway, tmp_path: Path) -> None:
    (tmp_path / "cases.yaml").write_text(CASES_YAML, encoding="utf-8")
    case = load_cases(tmp_path)[1]
    result = await run_case(case, gateway_url="http://gateway", judge_url="http://stub")
    assert result.kind == "judged"
    assert result.votes == [True] * 5
    assert result.passed is True
