# CWYD-7 — homelab homolog deploy

Runbook: [docs/deploy/homelab.md](../deploy/homelab.md).

## Images

Commit `e4edbf1` of `development` (CI green), published by the CI `publish` job:

| Image | Tag | Digest |
|---|---|---|
| `ghcr.io/victorgmrqs/chat-with-your-docs/backend` | `sha-e4edbf1` | `sha256:16cd5485a952eb2bb2a56ce1a41a6f6b7ad32380df84d9221004d87b17e6ed94` |
| `ghcr.io/victorgmrqs/chat-with-your-docs/frontend` | `sha-e4edbf1` | `sha256:ef3b1549c8e38ad9dfb6b5c49d1755419d217c0bc94253a4d60fa02de6660355` |

## GitOps PR

[victorgmrqs/homelab-gitops#106](https://github.com/victorgmrqs/homelab-gitops/pull/106), squash-merged
into `development` as `18f2b7d` (checks: `validate` with kubeconform, `gitleaks`, `links`, `gate`).
Before opening it, `kubectl apply --dry-run=server` accepted all 13 `cwyd` resources.

## homelab_deploy_success (2026-11-23)

```text
$ kubectl -n argocd get application homelab-homolog   # revision, sync, health
18f2b7d7192ef423114d9439885a42e0d0ee91a1 Synced Healthy

$ kubectl -n homolog get pods -l 'app in (cwyd-db,cwyd-backend,cwyd-frontend)'
NAME                             READY   STATUS    RESTARTS      AGE
cwyd-backend-58dc4dbfd4-dpvdf    1/1     Running   1 (12s ago)   87s
cwyd-db-0                        1/1     Running   0             87s
cwyd-frontend-67995f7ff6-zw4v8   1/1     Running   0             87s
```

The backend restarted once on this first deploy: its migration timed out while `cwyd-db` was still
running initdb. Fixed at the root by the `wait-db` initContainer (see "Follow-up" below).

Digests in use (pod `imageID`), equal to the published ones above:

```text
ghcr.io/victorgmrqs/chat-with-your-docs/backend@sha256:16cd5485a952eb2bb2a56ce1a41a6f6b7ad32380df84d9221004d87b17e6ed94
ghcr.io/victorgmrqs/chat-with-your-docs/frontend@sha256:ef3b1549c8e38ad9dfb6b5c49d1755419d217c0bc94253a4d60fa02de6660355
```

HTTPS through the ingress (wildcard certificate, HSTS from ingress-nginx, CSP from the app's nginx):

```text
$ curl -sI https://cwyd-homolog.lab.goncalvesmarques.com
HTTP/2 200
content-security-policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; ...
strict-transport-security: max-age=31536000; includeSubDomains
```

NetworkPolicy: a pod other than the frontend cannot reach the backend:

```text
$ kubectl -n homolog run np-probe --rm -i --restart=Never --image=busybox:1.37 -- \
    sh -c 'wget -q -T 5 -O- http://cwyd-backend:8000/health && echo REACHABLE || echo BLOCKED'
BLOCKED
```

Smoke test (re-run after the follow-up below, backend with 0 restarts):

```text
$ scripts/smoke.sh https://cwyd-homolog.lab.goncalvesmarques.com
== readiness
{"status":"ready","pgvector":"0.8.7"}
== upload
remote-work-policy.pdf -> 5b7fcef1-2d8e-4ba9-a53b-65d2712c47c6
expense-policy.pdf -> 785e911f-5b8e-47ed-ad4f-92aacc260737
parental-leave-policy.md -> f32cf3c2-75b1-4cec-a45e-1e3ebe97cd73
== indexing
5b7fcef1-2d8e-4ba9-a53b-65d2712c47c6 ready
785e911f-5b8e-47ed-ad4f-92aacc260737 ready
f32cf3c2-75b1-4cec-a45e-1e3ebe97cd73 ready
== coworking_two_sources
outcome=answered sources=expense-policy.pdf remote-work-policy.pdf
ok
== leave_split_not_covered
outcome=insufficient_evidence sources=
ok
SMOKE OK (https://cwyd-homolog.lab.goncalvesmarques.com)
```

## homelab_rollback_validation (2026-11-23)

In `homelab-gitops`, counting `name: cwyd*` in the rendered homolog overlay:

```text
current development 18f2b7d:                 23 cwyd names
git revert --no-commit 18f2b7d (then abort):  0 cwyd names   (12 files changed, 483 deletions)
parent 015a910 (overlay before the PR):      0 cwyd names
```

So reverting the deploy commit renders exactly the previous overlay, and Argo CD (prune enabled)
would remove the app. The PVC `data-cwyd-db-0` stays until deleted by hand (see the runbook).

## Follow-up: wait for the database

- [homelab-gitops#107](https://github.com/victorgmrqs/homelab-gitops/pull/107) (`0f44b58`): `wait-db`
  initContainer (`pg_isready`) so the backend no longer crash-restarts while initdb runs. The new
  pod hung in `Init` (the old pod kept serving): `pg_isready` printed `no attempt` because the pod
  UID 10001 has no passwd entry in the pgvector image.
- [homelab-gitops#108](https://github.com/victorgmrqs/homelab-gitops/pull/108) (`e52ef8a`): `-U cwyd`.
  Checked first with a probe pod (same labels and UID): without `-U` → `no attempt`, with it →
  `accepting connections`. After sync: Argo CD `e52ef8a Synced Healthy`, `deployment
  "cwyd-backend" successfully rolled out`, backend `RESTARTS 0`.

The init path on a fresh, empty volume was not re-run (the volume already holds data); it is the
same `pg_isready` loop, which only returns once the database accepts connections.
