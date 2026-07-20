# TODO(build): wire these targets to the scripts and stack. Enumerated final content:
#   up           -> docker compose up -d (floci + provider-stub)
#   seed         -> scripts/seed-aws.sh (SQS main+DLQ+redrive, DynamoDB tables, Secrets Manager secret)
#   kind-up      -> scripts/bootstrap-local.sh (kind cluster + KEDA + Argo Rollouts + kube-prometheus-stack)
#   deploy-local -> scripts/deploy-local.sh (build/load images into kind, kustomize apply local overlay)
#   eval         -> uv run python -m eval_harness.gate (run suite, write report, exit non-zero on gate fail)
#   test         -> uv run pytest (real)
#   lint         -> uv run ruff check . (real)
#   smoke-drain  -> scripts/smoke-stream-drain.sh (open SSE, trigger rollout, assert stream completes)

.PHONY: up seed kind-up deploy-local eval test lint smoke-drain

up:
	@echo "TODO(build): docker compose up -d  # floci + provider-stub"

seed:
	@echo "TODO(build): scripts/seed-aws.sh"

kind-up:
	@echo "TODO(build): scripts/bootstrap-local.sh"

deploy-local:
	@echo "TODO(build): scripts/deploy-local.sh"

eval:
	@echo "TODO(build): uv run python -m eval_harness.gate"

smoke-drain:
	@echo "TODO(build): scripts/smoke-stream-drain.sh"

lint:
	uv run ruff check .

test:
	uv run pytest
