# Local developer workflow. `up` + `seed` give a full stack against floci;
# `kind-up` + `deploy-local` exercise the Kubernetes path; `eval` runs the CI
# quality gate locally; `smoke-drain` proves the SSE drain invariant.

.PHONY: up seed kind-up deploy-local eval test lint smoke-drain

up:
	docker compose up -d --build floci provider-stub gateway

seed:
	bash scripts/seed-aws.sh

kind-up:
	bash scripts/bootstrap-local.sh

deploy-local:
	bash scripts/deploy-local.sh

eval:
	uv run python -m eval_harness.gate

smoke-drain:
	bash scripts/smoke-stream-drain.sh

lint:
	uv run ruff check .

test:
	uv run pytest
