# CWYD-20 — nginx hardening follow-up and Swagger UI behind /api

Evidence for the card's acceptance criteria. Outputs are verbatim (headers filtered with
`grep -iE`); nothing is mocked.

Environment: 2026-11-23, Docker 29.9.2, branch `feat/CWYD-20-nginx-hardening-swagger`. Both
images were built from the branch and run with the database image on a private Docker network:
web on `127.0.0.1:18080`, API on `127.0.0.1:18000` (published `:8000`), and a second API with
`API_DOCS_ENABLED=false` on `:18001`. The usual ports were taken by another stack.

Design (decided on the card, option 1): nginx sends `X-Forwarded-Prefix: /api` on `/api/*`, and
the API sets its root path only when the header equals `API_ROOT_PATH` (`/api`). Like
`uvicorn --root-path`, it prepends the prefix to the path too, so a proxied path that already has
it (`/api/api/chat` at nginx, outside the rate-limited locations of DOM-27) is a `404`. A first attempt
with `uvicorn --root-path /api` made `:8000/docs` ask for `/api/openapi.json`, which answered
`404` there; that run is recorded in the card comments.

```text
## Headers (curl -s -D -)
### GET http://localhost:18080/
HTTP/1.1 200 OK
Server: nginx
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
### GET http://localhost:18080/assets/index-Dukur3NX.js
HTTP/1.1 200 OK
Server: nginx
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
### GET http://localhost:18080/assets/missing.js
HTTP/1.1 404 Not Found
Server: nginx
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
### GET http://localhost:18080/api/health
HTTP/1.1 200 OK
Server: nginx
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
X-Frame-Options: DENY
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
### POST http://localhost:18080/api/documents (12 MB body, rejected by nginx)
HTTP/1.1 413 Request Entity Too Large
Server: nginx
X-Frame-Options: DENY
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
### nginx error page body (404 from the assets location): version shown?
nginx

## Swagger UI through the web server
### GET http://localhost:18080/api/docs: spec URL in the page
url: '/api/openapi.json'
[200]
### GET http://localhost:18080/api/openapi.json: servers
servers: [{'url': '/api'}] | openapi 3.1.0 | paths: 5
### Try it out on GET /health = {servers[0]}/health = http://localhost:18080/api/health
{"status":"ok"} [200]
### Doubled prefix through the web server (outside the rate-limited locations, DOM-27): 404
GET /api/api/health [404]
POST /api/api/chat [404]
POST /api/api/documents [404]
### Trailing slash through the web server: POST http://localhost:18080/api/chat/ redirects back into /api/chat
HTTP/1.1 307 Temporary Redirect
location: http://localhost/api/chat

## Direct access to the API (:8000 published as 18000)
### GET http://localhost:18000/docs
url: '/openapi.json'
[200]
### GET http://localhost:18000/openapi.json (what the direct docs page loads): servers
servers: (none) | paths: 5
### Try it out from the direct page: GET http://localhost:18000/health
{"status":"ok"} [200]
### Spoofed prefix sent straight to the API: X-Forwarded-Prefix: /evil
url: '/openapi.json'

## API_DOCS_ENABLED=false (second API container)
/docs 404
/redoc 404
/openapi.json 404
/api/docs 404
/health 200
```

- No nginx version in the `Server` header or in nginx's own error page; `Permissions-Policy` on
  the SPA, an asset, the 404, the API and the 413 (nginx's rejection).
- `/api/docs` through the web server loads `/api/openapi.json`, whose `servers` is `/api`, so
  "Try it out" on `GET /health` calls `/api/health` (200).
- `/api/api/...` through the web server answers `404`: no way around the rate limits. The
  trailing-slash redirect leads back into `/api/chat` (its host has no port because nginx
  forwards `Host $host`, unchanged by this card).
- `:8000/docs` still works: it loads `/openapi.json` (no `servers`). A spoofed prefix is ignored.
- `API_DOCS_ENABLED=false`: the docs routes answer `404`; `/health` stays `200`.
- `frontend/openapi.json`: `uv run python -m scripts.export_openapi` produces no diff (the export
  runs without the proxy header).
