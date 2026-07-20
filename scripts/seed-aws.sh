#!/usr/bin/env bash
# TODO(build): implement. Enumerated final content:
#   create SQS main queue + DLQ, set redrive policy maxReceiveCount=3 against floci :4566.
#   create DynamoDB idempotency + tickets tables.
#   put the managed-provider credential into Secrets Manager.
set -euo pipefail

echo "TODO(build): seed-aws.sh not implemented"
