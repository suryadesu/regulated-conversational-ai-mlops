"""Workspace-level smoke test: every scaffolded module imports with no side effects.

Encodes the plan's "imports clean" invariant as a CI-enforced test so the
`test` target and CI stay green while every module is still a placeholder.
"""

import importlib

MODULES = [
    "gateway.main",
    "gateway.config",
    "gateway.draining",
    "gateway.api.chat",
    "gateway.api.stream",
    "gateway.api.health",
    "gateway.providers.base",
    "gateway.providers.openai_compat",
    "gateway.providers.bedrock",
    "gateway.providers.retry",
    "gateway.providers.errors",
    "gateway.prompts.loader",
    "gateway.observability.metrics",
    "gateway.observability.tracing",
    "gateway.observability.scrubber",
    "provider_stub.main",
    "provider_stub.responses",
    "provider_stub.faults",
    "ticket_worker.main",
    "ticket_worker.consumer",
    "ticket_worker.idempotency",
    "ticket_worker.ticket",
    "eval_harness.runner",
    "eval_harness.assertions",
    "eval_harness.judge",
    "eval_harness.aggregate",
    "eval_harness.gate",
]


def test_all_modules_import() -> None:
    """Import every scaffolded module; a side effect or syntax error fails here."""
    for name in MODULES:
        importlib.import_module(name)
