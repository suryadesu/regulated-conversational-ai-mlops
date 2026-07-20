# Architecture & tradeoffs

Part 1 decisions are summarized here; the full system design lives in [README.md](../README.md).
Every claim about implemented behavior below is true of the code in this repository (the commit
history records each decision in its `Decisions:` body); production-evolution material is framed
explicitly as proposal.

## Design decisions

**Service shapes.** Both tracks hang off one seam: the `ProviderClient` protocol
(`gateway/providers/base.py`). The gateway, the ticket worker, the eval harness, and the canary
prober all reach models through it; managed (Bedrock `Converse`) and self-hosted
(OpenAI-compatible HTTP) are adapters behind it, so migrating a route between tracks is a
base-URL flip, not a rewrite. The worker consumes the gateway's contract as a real package
dependency — "same ProviderClient, same versioned prompt" is enforced by the import graph, not
by convention. The event path (SQS → claim → draft → persist → ack) keeps its failure story in
queue configuration: a poison message is simply never deleted, and `maxReceiveCount=3` redrive
plus a DynamoDB conditional-put idempotency claim give at-least-once delivery with exactly-once
side effects. Locally, the "managed provider" is a deterministic FastAPI stub with runtime fault
injection (`POST /__faults`, `fail_next` taking precedence over probabilistic bands so tests can
force exact failure counts) — evals and retry tests need deterministic content and injectable
failures, which no real API offers.

**Eval gate.** Deterministic assertions must pass 100%; judged cases take a ≥4/5 majority; the
suite gates at ≥90%. The gate runs as a blocking CI job against the real compose stack.

**Prompt versioning.** Prompts live at `prompts/<name>/vX.Y.Z.yaml` — no `latest` exists. The
hash-suffixed `gateway-env` ConfigMap pins `PROMPT_VERSION`, so a pin change alters the pod
template and rides the identical canary path as a code change. Rollback is `git revert`.

**Autoscaling metrics.** KEDA scales the gateway on `gateway_inflight_requests` (an I/O-bound
proxy saturates concurrency while CPU stays flat) and model serving on queue pressure — here the
gateway-side `gateway_upstream_inflight{upstream}` gauge, so one trigger works for llama.cpp
locally and vLLM in production. Utilization can't distinguish "busy" from "falling behind";
queue depth is the leading indicator of an SLO breach.

**Observability.** Five Prometheus metrics (tokens, duration, TTFT, cost, in-flight) with a
repo-versioned price table so $/1k-token assumptions are code-reviewable. The duration histogram
carries a `code` label because the canary error-rate query must separate 5xx from 2xx. An
unknown model or missing price file degrades to $0 cost rather than failing requests — cost is a
signal, not a gate. Retry policy: 429/500/502/503/504 only, exponential backoff with full jitter,
`Retry-After` honored as a delay floor, and never after the first streamed byte (a partial SSE
stream cannot be replayed without duplicating tokens).

**Deliberately kept simple:** regex-only PII floor (NER is the production follow-up); single
region; no Pushgateway — the canary prober POSTs its outcome to a gateway-internal endpoint that
sets `gateway_canary_probe_success`. Two lessons the build surfaced: per-service images
(`uv sync --frozen --no-dev --no-editable --package <name>`) are also the dependency-honesty
check — the shared workspace venv had masked an undeclared `sse-starlette` dependency and a
missing `__main__` guard; and emulator depth varies — floci's SQS/DynamoDB/Secrets apply cleanly
via Terraform, while its ECR spawns a real `registry:2` container and hangs without a Docker
socket, so the `ecr` module is count-gated off locally.

## Quality gates at scale

A gate a regulated bank can trust needs three properties: hermetic inputs, an explicit variance
model, and teeth. **Judge variance vs real regression:** each judged case generates one response
and judges it N=5 times, isolating judge-vote variance from generation variance. Vote splits are
classified in `evals/src/eval_harness/aggregate.py`: 0–1 passes is a consistent failure
(regression), anything wider is variance; the report artifact records per-case vote counts so a
reviewer can distinguish "the model got worse" from "the judge is noisy." An unparseable judge
reply is a failed vote, never a crashed suite. **Deterministic vs judged:** deterministic cases
(substring/regex/JSON-schema) encode hard requirements — a single failure blocks regardless of
overall rate; judged cases encode soft quality with a 90% suite threshold. An empty collected
suite also fails: a pipeline that loaded zero cases is broken, not vacuously green.
**Dataset curation and drift:** cases should grow from scrubbed production traffic — sample
transcripts weekly, redact through the same PII scrubber, and promote representative or
incident-derived prompts into the suite with review; retire cases whose intents no longer occur.
Drift between the eval distribution and production traffic is itself a reviewed metric.
**Cost and time budget:** in CI the judge is the deterministic stub, so the suite is hermetic,
reproducible, and runs in seconds for pennies; a nightly run points `EVAL_JUDGE_URL` at a real
model for realism without taxing every PR. **Necessary but not sufficient:** the gate samples a
fixed distribution pre-merge; production traffic is nonstationary. Post-merge, the same
assertions run online — the canary-prober Job replays golden prompts against the canary and its
outcome feeds Rollout analysis alongside error rate and p95, so a quality-only regression aborts
the rollout automatically. **Qualifying self-hosted models:** point the identical gate at the
candidate backend (a base-URL flip); it must clear the same deterministic floor and judged
threshold before any traffic shifts, then earn exposure through the same canary.

## Managed inference at scale

**Rate limits.** Managed APIs meter TPM and RPM independently, and which binds first is
workload-shaped: chat with long completions exhausts TPM long before RPM; document-vision calls
(many small requests, large image payloads, short text out) tend to hit RPM and payload caps.
The gateway therefore budgets both dimensions per route: `max_tokens` is a server-side setting,
never client-supplied, and per-intent routing picks the smallest model that clears the eval gate.
**Cost control:** model routing by intent, prompt caching (system prompts are pinned and
versioned, so cache keys are stable by construction — the provider-side prefix cache hits on
every request sharing a prompt version), and context budgets enforced at the gateway.
`gateway_cost_usd_total{route,model}` makes the build-vs-buy line item measurable per route.
**Throughput:** on-demand quota is elastic but throttleable at exactly the wrong time;
provisioned throughput buys guaranteed tokens/minute for the baseline while on-demand absorbs
burst. Provision the P50 of daily peak per critical route and let retries + fallback cover the
tail. **Failover and degradation:** the implemented ladder is retry (429/5xx, full jitter,
Retry-After honored, never mid-stream) → route-level base-URL flip to a secondary provider or
the self-hosted track (same `ProviderClient`, so the swap is config) → degrade: queue
non-interactive work (the SQS worker absorbs backlog by design), shed low-priority routes with
the documented 429 envelope, or route to a smaller model that passed the same gate. When a
provider is down entirely, chat degrades to the fallback provider per intent; ticket drafting
just accumulates in SQS and drains on recovery — that asymmetry is why the escalation path is a
queue, not an RPC.

## Self-hosted GPU serving and fleet management at scale

For 10–50 GPU nodes across 3 AZs in-region: **provisioning** via Karpenter over managed node
groups once past a handful of static nodes — MNGs (as authored in the `eks` module) are the
right bootstrap, but Karpenter consolidates, picks instance types from a weighted list
(g5/g6/p4d families per model size), and reacts to pending pods in seconds rather than ASG
minutes. Nodes run the EKS GPU AMI (pinned NVIDIA driver) with the device plugin publishing
`nvidia.com/gpu`; the GPU pool carries the `nvidia.com/gpu=present:NoSchedule` taint the serving
overlay tolerates, so nothing else lands on $30k hardware. **Spot vs on-demand:** spot for
stateless serving capacity with the 2-minute interruption notice wired to the same drain
choreography this repo implements for rollouts (readiness flips, in-flight requests finish,
bounded drain); on-demand or provisioned capacity for the baseline that must survive a spot
squeeze. Never run the only replica of a model on spot. **Autoscaling and idle cost:** pods
scale on queue depth (KEDA, as implemented); nodes follow via Karpenter consolidation.
Scale-to-zero applies only to off-peak pools and is honest about cold start: a 7B+ model load is
minutes, so pre-warmed nodes and an image + weights cache keep the cold path to model-load only.
**Health and remediation:** DCGM exporter feeds Prometheus (ECC error rates, thermal throttling,
NVLink faults); XID errors surface via Node Problem Detector conditions; automation cordons and
drains the node (same drain invariant), reschedules, and only pages a human when errors recur
across nodes — GPU faults are common enough at fleet scale that manual handling does not scale.
**Weights distribution:** the local initContainer + pinned-GGUF (URL + sha) pattern generalizes
to S3/FSx with node-local NVMe caching or streaming loaders; baking weights into images couples
a 20 GB artifact to every code change and is the wrong default. **In-region capacity is finite:**
GPU instance types stock out; mitigate with multi-family fallback lists, capacity reservations
for the baseline, and honest queueing when burst exceeds supply. **vLLM levers:**
`--gpu-memory-utilization 0.90` trades KV-cache headroom against OOM risk under long contexts;
continuous batching with `--max-num-seqs` trades throughput against per-request latency (the
knob that moves p95 first); `--tensor-parallel-size` shards models larger than one GPU at an
interconnect tax — never larger than the model requires; quantization (AWQ) roughly doubles
capacity at a quality cost that must re-clear the eval gate before rollout — the gate, not the
benchmark, decides.

## Data residency & compliance

**Exposure map.** On the managed track, the full prompt — system prompt plus customer utterances,
i.e. the highest-sensitivity payload in the platform — leaves the VPC to the provider's region;
locally that egress is the stub, in production it is the provider endpoint. What we log stays
scrubbed: metrics are aggregates, traces carry no prompt/completion content by default, and the
regex scrubber (emails, phones, Luhn-gated PANs, IBANs) floors anything exported. Its honest gap:
names, addresses, and free-text context need an NER pass — the first production investment.
**Technical controls:** pin regional endpoints so inference terminates in-jurisdiction; keep raw
prompts out of telemetry by default; TLS everywhere; KMS-encrypted storage for tickets and
transcripts; the provider credential lives in Secrets Manager and reaches pods via
IRSA-scoped External Secrets, never in the repo. **The cross-region inference-profile nuance:**
managed platforms increasingly route through inference profiles that may execute in any region
of a geography for capacity reasons — "the endpoint is in-region" no longer implies "the
computation stayed in-region." Residency requires pinning to single-region profiles (accepting
throughput limits) or contractually constraining the routing set, and evidencing it.
**Contractual controls:** DPA with zero-data-retention riders, no training on customer data,
subprocessor lists, breach-notification windows, audit rights. **Audit evidence:** immutable
eval reports per merge (CI artifacts), scrubbed traces, prompt-version history in git, the
commit-level decision log this repo maintains, and CloudTrail on the AWS side — together they
answer "what model, what prompt version, what quality bar, what data path" for any past request.
**Residency as forcing function:** if the home jurisdiction cannot be satisfied contractually,
self-hosting stops being a cost decision — it becomes the only compliant architecture, and the
Track 2 assets here are the prepared landing zone.

## Migration, build vs buy, and 100x scale

**Build vs buy.** Buy while quality-per-dollar on managed APIs beats your all-in self-hosted
cost; build when volume, residency, or latency variance flips the inequality.
`gateway_cost_usd_total{route,model}` gives the per-route managed spend directly. Compare against
GPU-fleet TCO: instance cost (a modest 8-GPU baseline runs ~$1–2M/yr on-demand), plus idle
capacity you cannot avoid provisioning, plus the real line item — 2–3 engineers of permanent
operational ownership (driver/AMI upgrades, capacity planning, incident rotation). Break-even
only arrives when sustained (not peak) token volume on specific routes prices above the fleet
that could serve them; residency (above) can force the move earlier regardless of cost.
**Exit criteria, pre-committed:** migrate a route only when the self-hosted backend clears the
same eval gate at parity, p95 within SLO at projected load, cost-per-1k-tokens under the managed
price at sustained volume, and a manned on-call rotation exists; abort (fall back to managed —
one config flip) if canary analysis fails twice or quality drifts below the gate for a week.
**Migration sequence:** shadow (mirror traffic, compare offline via the same eval suite) →
qualify (gate at parity) → route-level canary by intent with managed fallback (start with
lowest-risk intents; the platform's canary + prober machinery applies unchanged because both
backends speak the same contract) → ramp intent by intent, watching the same SLO and quality
signals. **100x overnight, what breaks first, in order:** (1) provider TPM/RPM — retries turn a
throttle into a self-inflicted DDoS unless backpressure sheds early; buy provisioned throughput,
route across providers. (2) Cost — linear with volume and now material; enforce per-route
budgets on the existing cost counter, cache aggressively, downgrade models per intent. (3) SQS
consumer lag — the queue absorbs the spike by design; KEDA scales workers to the cap, then
backlog age (not depth) is the alarm. (4) DynamoDB — on-demand mode absorbs most of it; watch
for hot partition keys on idempotency claims. (5) The streaming load balancer — hundreds of
thousands of long-lived SSE connections exhaust LB and pod connection tables before CPU;
raise idle timeouts, scale on in-flight (already the signal), add connection-aware sharding.
(6) GPU capacity — in-region supply is the hard wall; provisioned capacity + multi-family
fallback + queueing. (7) Cold start — scale-up that takes minutes is too slow for a 100x step
change; pre-warmed pools and cache-backed model loads are the only mitigation.

## What you cut

Deprioritized for time, in the order I would implement them in production:

1. **NER-based PII scrubbing** — the regex floor (emails, phones, Luhn-gated PANs, IBANs) misses
   names, addresses, and free-text context; a regulated bank needs the NER pass before any
   telemetry leaves the platform. First thing I'd build.
2. **Shadow traffic replay** — mirror a production slice against candidate backends to gather
   quality/cost evidence before any canary; prerequisite for confident managed→self-hosted moves.
3. **Per-tenant cost budgets with enforcement** — the `gateway_cost_usd_total` labeling already
   supports it; add budget objects and a shedding policy.
4. **vLLM prefix caching** tuned to the pinned system prompts (stable cache keys exist by
   construction) to cut prefill cost on the self-hosted track.
5. **Multi-region active/active** with regional provider failover.
6. **Simplifications accepted in this build:** judged evals in CI use the deterministic stub
   judge (nightly realism run instead); the canary prober reports through a gateway endpoint
   rather than a Pushgateway; prompt files ship in the image with the ConfigMap pinning only the
   version; floci's ECR is count-gated off locally (no Docker socket); the kind e2e runs
   nightly/manual rather than blocking PRs.
