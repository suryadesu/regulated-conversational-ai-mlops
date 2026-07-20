# Prompt store

- Prompts are versioned at `prompts/<name>/vX.Y.Z.yaml`; there is no `latest`.
- Each environment overlay pins an explicit `PROMPT_VERSION`; a kustomize `configMapGenerator` mounts exactly that version (hash-suffixed).
- A prompt change is a PR + rollout, reviewable as a diff — never a code edit.
- Rollback is `git revert` plus the previous hash-suffixed ConfigMap still existing.
- Keys per file: `id`, `version`, `system`, `variables`.
