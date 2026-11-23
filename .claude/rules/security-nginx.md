---
paths:
  - "frontend/nginx/**"
---

# nginx security headers and limits

- Security headers are declared once, at `server` level, with `always`, so 4xx/5xx responses
  (nginx's own 404 and 413 included) carry them too. `add_header_inherit merge;` (nginx
  1.29.3+) keeps them in locations that declare their own `add_header` (`/assets/`
  `Cache-Control`): never re-include a header snippet per location.
- Baseline on every response: `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`.
- The CSP is `'self'`-only with `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'self'`
  and `form-action 'self'`. No `'unsafe-inline'`, `'unsafe-eval'`, CDN or wildcard source: the
  SPA bundles its scripts, styles and fonts. A change that needs one is a design change, not a
  header edit. Check it with a headless browser listening to `securitypolicyviolation`.
- The CSP comes from `map $uri $content_security_policy`, which returns `""` under `/api/`
  (nginx sends no header for an empty value). JSON needs no CSP, and Swagger UI uses an inline
  script. Add a new path-dependent header the same way, not with `if`.
- HSTS is not set here: TLS ends at the ingress, which owns it (CWYD-7).
- Body size: `client_max_body_size` on `/api/` stays just above `MAX_UPLOAD_MB` and returns the
  API's JSON error shape (`@upload_too_large`), so nginx rejects with 413 before the body
  reaches the backend.
- Rate limits (target, CWYD-18) use `limit_req_zone` keyed on the client address with
  `limit_req_status 429` (the default 503 reads as an outage) and a JSON body in the API's
  error shape. Upload and question routes get their own zones.
- `real_ip_header X-Forwarded-For` (target, CWYD-20) only together with `set_real_ip_from`
  listing the trusted proxy CIDRs; never `0.0.0.0/0`. Without it the rate-limit key is the
  proxy, or a value the client spoofs.
- Never log request bodies or query strings that can hold question text. Never set
  `server_tokens on`; never expose `stub_status` or autoindex.
- Evidence for header changes: `curl -s -D - -o /dev/null` against `/`, an asset, a 404, an
  `/api/` route and the 413 (see `docs/evidence/CWYD-14-headers.md`).

Sources: OWASP Secure Headers Project and HTTP Headers Cheat Sheet; MDN CSP;
nginx `ngx_http_headers_module` (`add_header_inherit`), `ngx_http_limit_req_module`,
`ngx_http_realip_module`; decisions in CWYD-14.
