# Browser Session Management

Run multiple isolated browser sessions against this project's Compose stack. Sessions are headless by default.

## Named Browser Sessions

Use `-s` flag to isolate browser contexts:

```bash
# Browser 1: Authentication flow
playwright-cli -s=auth open "$E2E_BASE_URL/login"

# Browser 2: Public browsing (separate cookies, storage)
playwright-cli -s=public open "$E2E_BASE_URL"

# Commands are isolated by browser session
playwright-cli -s=auth fill e1 "$E2E_USER"
playwright-cli -s=public snapshot
```

## Browser Session Isolation Properties

Each browser session has independent:
- Cookies
- LocalStorage / SessionStorage
- IndexedDB
- Cache
- Browsing history
- Open tabs

## Browser Session Commands

```bash
# List all browser sessions
playwright-cli list

# Stop a browser session (close the browser)
playwright-cli close                # stop the default browser
playwright-cli -s=mysession close   # stop a named browser

# Stop all browser sessions
playwright-cli close-all

# Forcefully kill all daemon processes (for stale/zombie processes)
playwright-cli kill-all

# Delete browser session user data (profile directory)
playwright-cli delete-data                # delete default browser data
playwright-cli -s=mysession delete-data   # delete named browser data
```

A headless session shuts down on its own after an hour without commands; the next command then reports that the browser is not open, so run `open` again. Headed browsers stay open. Use `open --idle-timeout=<ms>` to change the timeout, or `0` to disable it.

## Environment Variable

Set a default browser session name via environment variable:

```bash
export PLAYWRIGHT_CLI_SESSION="mysession"
playwright-cli open "$E2E_BASE_URL"  # Uses "mysession" automatically
```

## Common Patterns

### A/B Testing Sessions

```bash
# Test different user experiences
playwright-cli -s=variant-a open "$E2E_BASE_URL?variant=a"
playwright-cli -s=variant-b open "$E2E_BASE_URL?variant=b"

# Compare
playwright-cli -s=variant-a screenshot
playwright-cli -s=variant-b screenshot
```

### Persistent Profile

By default, browser profile is kept in memory only. Use `--persistent` flag on `open` to persist the browser profile to disk:

```bash
# Use persistent profile (auto-generated location)
playwright-cli open "$E2E_BASE_URL" --persistent

# Persistent profiles keep cookies/tokens on disk: delete with delete-data when done
```

## Default Browser Session

When `-s` is omitted, commands use the default browser session:

```bash
# These use the same default browser session
playwright-cli open "$E2E_BASE_URL"
playwright-cli snapshot
playwright-cli close  # Stops default browser
```

## Browser Session Configuration

Configure a browser session with specific settings when opening:

```bash
# Open with config file
playwright-cli open "$E2E_BASE_URL" --config=.playwright/my-cli.json

# Open with specific browser
playwright-cli open "$E2E_BASE_URL" --browser=firefox

# Open in headed mode
playwright-cli open "$E2E_BASE_URL" --headed   # only when the user asks (default is headless)

# Open with persistent profile
playwright-cli open "$E2E_BASE_URL" --persistent
```

## Best Practices

### 1. Name Browser Sessions Semantically

```bash
# GOOD: Clear purpose
playwright-cli -s=admin-login open "$E2E_BASE_URL/login"
playwright-cli -s=upload-flow open "$E2E_BASE_URL"

# AVOID: Generic names
playwright-cli -s=s1 open "$E2E_BASE_URL"
```

### 2. Always Clean Up

```bash
# Stop browsers when done
playwright-cli -s=auth close
playwright-cli -s=upload-flow close

# Or stop all at once
playwright-cli close-all

# If browsers become unresponsive or zombie processes remain
playwright-cli kill-all
```

### 3. Delete Stale Browser Data

```bash
# Remove old browser data to free disk space
playwright-cli -s=oldsession delete-data
```
