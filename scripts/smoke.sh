#!/usr/bin/env bash
# End-to-end smoke test through the web entrypoint (nginx /api), for any environment:
#   scripts/smoke.sh http://localhost:8080                           # docker compose
#   scripts/smoke.sh https://cwyd-homolog.lab.goncalvesmarques.com   # homelab homolog (CWYD-7)
# Checks readiness, uploads three fixtures, waits until they are ready, then runs two cases from
# backend/tests/fixtures/rag_cases.json: a two-source answer and an insufficient-evidence answer
# (outcome and source filenames). Needs curl and python3. Safe to repeat: re-uploading the same
# file returns the existing document. Its 3 uploads use the upload burst (6/min, burst 3): run it
# at most once a minute, or a 429 fails the upload step.
set -euo pipefail

BASE=${1:?usage: scripts/smoke.sh <base-url>}
API="${BASE%/}/api"
FIXTURES="$(cd "$(dirname "$0")/.." && pwd)/backend/tests/fixtures"
TIMEOUT=${SMOKE_TIMEOUT:-180}
CASES=(coworking_two_sources leave_split_not_covered)

fail() { echo "FAIL: $*" >&2; exit 1; }
json() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; } # json '<expr on d>'

echo "== readiness"
curl -fsS "$API/health/ready" || fail "backend not ready"
echo

echo "== upload"
ids=()
for f in remote-work-policy.pdf expense-policy.pdf parental-leave-policy.md; do
  id=$(curl -fsS -F "file=@$FIXTURES/documents/$f" "$API/documents" | json "d['id']") || fail "upload $f"
  echo "$f -> $id"
  ids+=("$id")
done

echo "== indexing"
deadline=$((SECONDS + TIMEOUT))
for id in "${ids[@]}"; do
  while :; do
    status=$(curl -fsS "$API/documents/$id" | json "d['status']") || fail "status $id"
    [ "$status" = ready ] && break
    [ "$status" = failed ] && fail "document $id failed"
    [ "$SECONDS" -lt "$deadline" ] || fail "document $id still $status after ${TIMEOUT}s"
    sleep 2
  done
  echo "$id ready"
done

for case_id in "${CASES[@]}"; do
  echo "== $case_id"
  case_json=$(json "json.dumps(next(c for c in d['cases'] if c['id'] == '$case_id'))" \
    <"$FIXTURES/rag_cases.json")
  body=$(json "json.dumps({'question': d['question']})" <<<"$case_json")
  answer=$(curl -fsS -H 'Content-Type: application/json' -d "$body" "$API/chat")
  # Prints the observed result, then "ok" or the expectation that failed.
  python3 -c '
import json, sys
case, answer = json.loads(sys.argv[1]), json.loads(sys.argv[2])
got = " ".join(sorted({s["filename"] for s in answer["sources"]}))
want = " ".join(sorted({s["filename"] for s in case["expected_sources"]}))
print("outcome=%s sources=%s" % (answer["outcome"], got))
ok = answer["outcome"] == case["expected_outcome"] and got == want
print("ok" if ok else "expected outcome=%s sources=%s" % (case["expected_outcome"], want))
sys.exit(0 if ok else 1)
' "$case_json" "$answer" || fail "$case_id"
done

echo "SMOKE OK ($BASE)"
