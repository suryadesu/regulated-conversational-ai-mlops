# Architecture & tradeoffs

Part 1 decisions are summarized here; the full system design lives in [README.md](../README.md).
This document accretes decisions commit-by-commit during implementation — each entry cites the
behavior actually built in this repository, then describes how it evolves for a production
banking environment.

## Design decisions

- **One `ProviderClient` protocol over both tracks.** The gateway, the ticket worker, the eval
  suite, and the canary prober all speak to models through the same protocol
  (`gateway/providers/base.py`): managed (Bedrock) and self-hosted (OpenAI-compatible) are
  adapters behind it. Migrating a route between tracks is a base-URL flip, not a rewrite.
- **Deterministic stub over floci's Bedrock stub for the primary local path.** Evals and retry
  tests need deterministic content and injectable failures (429/5xx/latency via `POST /__faults`);
  floci's Bedrock endpoint is still exercised by the `bedrock` adapter as a smoke path.
  Stub behaviors fixed during implementation: `fail_next` takes precedence over probabilistic
  fault bands so tests can force exact failure counts; a canned-response cache miss falls back to
  a hash-tagged echo (`[stub:<sha256[:16]>] Acknowledged: ...`) instead of raising, so every
  prompt has a stable, assertable reply without pre-authoring.
- **Adapter seams are test-injection points, not abstractions.** `OpenAICompatProvider` takes an
  optional httpx transport (MockTransport in tests, real network in production); Bedrock tests use
  botocore's `Stubber` so request/response shapes are validated against the real service model.
  Bedrock's `ConverseStream` is drained inside the offloaded thread — bounded token streams don't
  justify bridging a sync iterator across the event loop live.
- **SSE graceful drain choreography**: `preStop: sleep 10` (endpoint-slice propagation) →
  readiness flips 503 while liveness stays 200 → in-flight counter bounds drain at 160 s →
  `terminationGracePeriodSeconds: 180`. Invariant: a rolling deploy never cuts an open stream.
- **Prompt pinning**: `prompts/<name>/vX.Y.Z.yaml`, no `latest`; each overlay pins
  `PROMPT_VERSION`; hash-suffixed ConfigMap puts prompt rollbacks on the same canary path as code.
- **Autoscaling metrics**: KEDA on `gateway_inflight_requests` (I/O-bound proxy — CPU stays flat
  under saturation) and queue depth for the batch engine (utilization can't distinguish "busy"
  from "falling behind").
- **Observability**: five Prometheus metrics (tokens, duration, TTFT, cost, in-flight) with a
  repo-versioned price table so $/1k-token assumptions are code-reviewable. The duration
  histogram carries a `code` label so the canary analysis can compute a 5xx error rate; an
  unknown model or missing price file degrades to $0 cost rather than failing requests —
  cost is a signal, not a gate.
- **Ticket worker reuses the gateway's contract as a real dependency.** `ticket-worker` depends on
  the `gateway` workspace package and imports `ProviderClient`/`PromptTemplate`/`Message` directly —
  "same ProviderClient, same versioned prompt" is enforced by the import graph, not by convention.
  Poison messages are deliberately left undeleted (no manual DLQ code): SQS visibility timeout +
  `maxReceiveCount=3` redrive is the whole failure path, and a redelivered already-processed event
  hits the DynamoDB conditional-put claim and is acked without re-executing the side effect.
- **Deliberately kept simple**: regex-only PII floor (NER is the production follow-up), single
  region, no Pushgateway (the canary prober reports through a gateway-internal endpoint instead).

## Quality gates at scale

- Deterministic cases must pass 100%; judged cases run N=5 with a ≥4/5 majority; suite gate ≥90%.
- Judge variance vs real regression: vote-split classification (0–1 of 5 passes = regression,
  otherwise variance) implemented in `evals/src/eval_harness/aggregate.py`; the report artifact
  records per-case vote counts.
- CI judge is the hermetic deterministic stub; a nightly run points at the real model for realism.
- Dataset curation: cases grow from scrubbed production traffic; drift reviewed on a cadence.
- CI cost/time budget: small sequential suite against the stub — seconds, not minutes.
- The gate is necessary but not sufficient: online evals continue post-merge via the canary-prober
  Job feeding Rollout analysis (`canary_probe_success`).
- The same gate, pointed at a self-hosted backend, qualifies it before any traffic shifts.

## Managed inference at scale

- Rate limits: TPM vs RPM — which binds first differs for chat (long completions, TPM-bound) vs
  document vision (bursty, RPM-bound).
- Cost control: model routing by intent, prompt caching, gateway-enforced context/token budgets
  (`max_tokens` is a server-side setting, not client-supplied).
- Throughput: on-demand quota vs provisioned throughput tradeoffs.
- Failover: retry policy (429/500/502/503/504, exponential backoff + full jitter, Retry-After
  honored, never after first streamed byte) → route-level base-URL flip to a fallback provider →
  degradation modes (queue, shed, smaller model).

## Self-hosted GPU serving and fleet management at scale

- 10–50 GPU nodes across multiple AZs: node lifecycle, instance selection, Karpenter vs managed
  node groups, GPU AMI + driver + device plugin.
- Spot vs on-demand and interruption handling — the same drain choreography applies at node level.
- Pod- and node-level autoscaling with idle-cost control; scale-to-zero honesty: GPU model load
  is minutes, so it applies only to off-peak pools with pre-warmed nodes and image/model caches.
- GPU health: DCGM metrics + XID errors surfaced via Node Problem Detector; automated
  cordon/drain remediation.
- Model-weights distribution and cold start: bake vs volume vs streaming; the local
  initContainer + pinned-GGUF pattern is the analog.
- In-region GPU capacity constraints.
- vLLM levers: `--gpu-memory-utilization` (KV-cache headroom vs OOM), continuous batching /
  `--max-num-seqs` (throughput vs per-request latency), `--tensor-parallel-size` (models larger
  than one GPU), quantization (capacity/throughput vs quality).

## Data residency & compliance

- PII exposure map of the inference path: what leaves the VPC, what is logged where.
- Technical controls: regional endpoint pinning, regex scrubber floor (emails/phones/PAN-with-Luhn/
  IBAN) with its honest NER gap, raw prompts/completions never exported by default.
- Contractual controls: DPA, zero-data-retention riders.
- Cross-region inference-profile nuance: managed APIs may route across regions unless pinned.
- Audit evidence: scrubbed traces, immutable eval reports, prompt-version history in git,
  commit-level decision log (this repo's convention).
- Residency as a forcing function in the bring-inference-in-house decision.

## Migration, build vs buy, and 100x scale

- Break-even reasoning: `gateway_cost_usd_total` per route vs GPU-fleet TCO (nodes + engineers +
  idle capacity); explicit exit criteria; honest operational cost of owning a fleet.
- Migration sequence: shadow traffic → the same eval gate → route-level canary by intent with
  managed fallback → ramp.
- 100x overnight failure ordering: provider TPM limits first, then cost, SQS consumer lag,
  DynamoDB write throughput, streaming LB connection limits, GPU capacity, cold start — with the
  first fix for each.

## What you cut

- NER-based PII scrubbing (regex floor only) — the first thing to implement in a real production
  rollout.
- Shadow traffic replay.
- Per-tenant cost budgets with enforcement.
- vLLM prefix caching for shared system-prompt prefixes.
- Multi-region active/active with regional provider failover.
