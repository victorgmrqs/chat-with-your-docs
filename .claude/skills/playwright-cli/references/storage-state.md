# Storage Management

Manage cookies, localStorage, sessionStorage, and browser storage state.

## Storage State

Save and restore complete browser state including cookies and storage.

### Save Storage State

```bash
# State files contain cookies/tokens: always write them under .playwright-cli/ (gitignored)
playwright-cli state-save .playwright-cli/auth-state.json
```

### Restore Storage State

```bash
# Load storage state from file
playwright-cli state-load .playwright-cli/auth-state.json

# Reload page to apply cookies
playwright-cli open "$E2E_BASE_URL"
```

### Storage State File Format

The saved file contains:

```json
{
  "cookies": [
    {
      "name": "session_id",
      "value": "abc123",
      "domain": "example.com",
      "path": "/",
      "expires": 1893456000,
      "httpOnly": true,
      "secure": true,
      "sameSite": "Lax"
    }
  ],
  "origins": [
    {
      "origin": "https://example.com",
      "localStorage": [
        { "name": "theme", "value": "dark" },
        { "name": "user_id", "value": "12345" }
      ]
    }
  ]
}
```

## Cookies

### List All Cookies

```bash
playwright-cli cookie-list
```

### Filter Cookies by Domain

```bash
playwright-cli cookie-list --domain=example.com
```

### Filter Cookies by Path

```bash
playwright-cli cookie-list --path=/api
```

### Get Specific Cookie

```bash
# Prints a session value to the terminal: never pipe it into logs, commits or tickets
playwright-cli cookie-get session_id
```

### Set a Cookie

```bash
# Basic cookie
playwright-cli cookie-set session abc123

# Cookie with options
playwright-cli cookie-set session abc123 --domain=example.com --path=/ --httpOnly --secure --sameSite=Lax

# Cookie with expiration (Unix timestamp)
playwright-cli cookie-set remember_me token123 --expires=1893456000
```

### Delete a Cookie

```bash
playwright-cli cookie-delete session_id

# Only on one domain, other domains keep their session_id
playwright-cli cookie-delete session_id --domain=example.com
```

### Clear All Cookies

```bash
playwright-cli cookie-clear
```

### Advanced: Multiple Cookies or Custom Options

For complex scenarios like adding multiple cookies at once, use `run-code`:

```bash
playwright-cli run-code "async page => {
  await page.context().addCookies([
    { name: 'session_id', value: 'sess_abc123', domain: 'example.com', path: '/', httpOnly: true },
    { name: 'preferences', value: JSON.stringify({ theme: 'dark' }), domain: 'example.com', path: '/' }
  ]);
}"
```

## Local Storage

### List All localStorage Items

```bash
playwright-cli localstorage-list
```

### Get Single Value

```bash
playwright-cli localstorage-get token
```

### Set Value

```bash
playwright-cli localstorage-set theme dark
```

### Set JSON Value

```bash
playwright-cli localstorage-set user_settings '{"theme":"dark","language":"en"}'
```

### Delete Single Item

```bash
playwright-cli localstorage-delete token
```

### Clear All localStorage

```bash
playwright-cli localstorage-clear
```

### Advanced: Multiple Operations

For complex scenarios like setting multiple values at once, use `run-code`:

```bash
playwright-cli run-code "async page => {
  await page.evaluate(() => {
    localStorage.setItem('token', 'jwt_abc123');
    localStorage.setItem('user_id', '12345');
    localStorage.setItem('expires_at', Date.now() + 3600000);
  });
}"
```

## Session Storage

### List All sessionStorage Items

```bash
playwright-cli sessionstorage-list
```

### Get Single Value

```bash
playwright-cli sessionstorage-get form_data
```

### Set Value

```bash
playwright-cli sessionstorage-set step 3
```

### Delete Single Item

```bash
playwright-cli sessionstorage-delete step
```

### Clear sessionStorage

```bash
playwright-cli sessionstorage-clear
```

## IndexedDB

### List Databases

```bash
playwright-cli run-code "async page => {
  return await page.evaluate(async () => {
    const databases = await indexedDB.databases();
    return databases;
  });
}"
```

### Delete Database

```bash
playwright-cli run-code "async page => {
  await page.evaluate(() => {
    indexedDB.deleteDatabase('myDatabase');
  });
}"
```

## Common Patterns

### Authentication State Reuse

```bash
# Step 1: Login and save state
playwright-cli open "$E2E_BASE_URL/login"
playwright-cli snapshot
playwright-cli fill e1 "$E2E_USER"
playwright-cli fill e2 "$E2E_PASSWORD"
playwright-cli click e3

# Save the authenticated state
playwright-cli state-save .playwright-cli/auth.json

# Step 2: Later, restore state and skip login
playwright-cli state-load .playwright-cli/auth.json
playwright-cli open "$E2E_BASE_URL/dashboard"
# Already logged in!
```

### Save and Restore Roundtrip

```bash
# Set up authentication state
playwright-cli open "$E2E_BASE_URL"
playwright-cli eval "() => { document.cookie = 'session=abc123'; localStorage.setItem('user', 'john'); }"

# Save state to file
playwright-cli state-save .playwright-cli/my-session.json

# ... later, in a new session ...

# Restore state
playwright-cli state-load .playwright-cli/my-session.json
playwright-cli open "$E2E_BASE_URL"
# Cookies and localStorage are restored!
```

## Security Notes

- Never commit storage state files containing auth tokens
- State files live under `.playwright-cli/` and `auth*.json` is gitignored (see the repo `.gitignore`); verify before saving anywhere else
- Delete state files after automation completes
- Read credentials from fixtures or env vars (`$E2E_USER`, `$E2E_PASSWORD`), never literals; do not paste state files, cookies or tokens into tickets or PRs
- By default, sessions run in-memory mode which is safer for sensitive operations
