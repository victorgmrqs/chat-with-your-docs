# CWYD-18 — Rate limits at the web server

Evidence for the card's acceptance criteria (DOM-27). Outputs are verbatim; nothing is mocked.

Environment: 2026-11-23, Docker 29.9.2, branch `feat/CWYD-18-nginx-rate-limits`. The web image
was built from the branch (`docker build frontend`) and run with the database and API images on
a private Docker network, published on `127.0.0.1:18080` (the usual ports were taken by another
stack). `nginx -t` inside the container: `configuration file /etc/nginx/nginx.conf test is
successful`. No document was Ready, so questions that pass the limit get the API's
`409 no_ready_documents`.

## Default limits: bursts, envelope, headers, polling

Script: back-to-back `curl` calls against `http://localhost:18080`. The "9th request" block is
filtered to drop `Date`, `Server`, `Connection` and `Content-Length`.

```text
### Chat burst: 8 POST /api/chat back to back (rate 10r/m, burst 5)
1:409 2:409 3:409 4:409 5:409 6:409 7:429 8:429 
### The 9th request, headers and body
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 60
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
X-Frame-Options: DENY

{"code":"rate_limited","detail":"Too many requests. Try again in a minute."}

### Upload burst: 5 POST /api/documents back to back (rate 6r/m, burst 3)
1:202 2:200 3:200 4:200 5:429 
### Status polling: 20 GET /api/documents right after the upload burst (not limited)
200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 
### Other routes unaffected: GET /api/health and GET / after the bursts
GET /api/health 200
GET / 200
```

- Questions: 1 + burst 5 reach the API, the rest get `429` (`RATE_LIMIT_CHAT=10r/m`, burst 5).
- Uploads: 1 + burst 3 reach the API (`202`, then `200` for the same file, DOM-04), the 5th gets
  `429` (`RATE_LIMIT_UPLOAD=6r/m`, burst 3).
- The `429` carries the API envelope, `Retry-After: 60` and the CWYD-14 headers (no CSP: it is
  an `/api/` response, as designed).
- Listing/polling and other routes are not limited.

## Changing the limits and concurrent questions

A second web container with `RATE_LIMIT_CHAT=600r/m`, `RATE_LIMIT_CHAT_BURST=50` and
`RATE_LIMIT_CHAT_CONNECTIONS=2`, proxying to a stub backend that answers `POST /chat` after 3 s,
so four parallel questions overlap. The rendered config shows the substituted values.

```text
### Rendered limits with RATE_LIMIT_CHAT=600r/m, RATE_LIMIT_CHAT_BURST=50, RATE_LIMIT_CHAT_CONNECTIONS=2
limit_req_zone $binary_remote_addr zone=chat:10m rate=600r/m;
limit_req_zone $upload_limit_key zone=uploads:10m rate=6r/m;
limit_req zone=chat burst=50 nodelay;
limit_conn chat_connections 2;
limit_req zone=uploads burst=3 nodelay;
### 4 concurrent POST /api/chat to a backend that takes 3 s (connection limit 2)
  2 200
  2 429
```

- The environment overrides the image defaults (the upload values keep their defaults).
- With 2 questions in progress, the 3rd and 4th parallel ones get `429` from `limit_conn`.
