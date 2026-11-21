---
name: playwright-cli
description: Playwright CLI for end-to-end testing and debugging of this project's React frontend against the Docker Compose stack: drive the browser headless, take snapshots, inspect console and network, write and debug Playwright tests. Not for backend tests, Vitest unit tests or general web scraping.
license: Apache-2.0
---

## Project overrides

These rules come from the project and win over anything below.

- Scope: E2E testing and debugging of this project's frontend only. Do not browse or scrape third-party sites.
- Base URL: the frontend served by the Docker Compose stack (read it from the `E2E_BASE_URL` env var or the Compose config; start the stack with `docker compose up -d` first). Never hardcode a different host.
- Headless by default (the default of `open`); use `--headed` only when the user asks.
- Credentials: never write usernames or passwords as literals in commands, tests or docs. Read them from fixtures or env vars (e.g. `$E2E_USER`, `$E2E_PASSWORD`). Never print them.
- Auth state files (`state-save`), cookies, traces and request/response dumps may contain tokens and session cookies. Keep them under `.playwright-cli/` (gitignored), never commit them, never paste them in tickets or PRs, and delete them after use (`playwright-cli delete-data`, remove `auth*.json` and trace output).
- Run the CLI through the locally pinned version: `npx --no-install playwright cli ...` (needs Playwright 1.59 or newer; check `npx --no-install playwright --version`). Never install anything (including `@playwright/cli` or browsers) without asking the user first.
- Prefer role-based locators (`getByRole`, `getByLabel`) and refs from snapshots; use `getByTestId` only when no accessible name exists.
- Prefer web-first assertions and explicit conditions in tests; do not wait on `networkidle`.
- Mock only at the boundary when a test needs it (see request-mocking); E2E should exercise the real stack by default.
- The Playwright CLI is preferred over Playwright MCP in this project.
- Examples below use `playwright-cli`; in this project prefix each with `npx --no-install playwright cli` unless the user has a global install.


# Browser Automation with playwright-cli

## Quick start

```bash
# open new browser
playwright-cli open
# navigate to a page
playwright-cli goto "$E2E_BASE_URL"
# interact with the page using refs from the snapshot
playwright-cli click e15
playwright-cli type "search query"
playwright-cli press Enter
# take a screenshot (rarely used, as snapshot is more common)
playwright-cli screenshot
# close the browser
playwright-cli close
```

## Commands

### Core

```bash
playwright-cli open
# open and navigate right away
playwright-cli open "$E2E_BASE_URL"
playwright-cli goto "$E2E_BASE_URL/login"
playwright-cli type "search query"
playwright-cli click e3
playwright-cli dblclick e7
# --submit presses Enter after filling the element
playwright-cli fill e5 "$E2E_USER"  --submit
playwright-cli drag e2 e8
# drop files or data onto an element (from outside the page)
playwright-cli drop e4 --path=./image.png
playwright-cli drop e4 --data="text/plain=hello world"
playwright-cli hover e4
playwright-cli select e9 "option-value"
playwright-cli upload ./document.pdf
playwright-cli check e12
playwright-cli uncheck e12
playwright-cli snapshot
# search the snapshot for text or a regexp, returns matching nodes with surrounding context
playwright-cli find "Sign in"
playwright-cli find --regex "Sign (in|up)"
# wrap the regexp in slashes to add flags, e.g. /i for case-insensitive
playwright-cli find --regex "/sign (in|up)/i"
# save results to a file when a query produces too many matches
playwright-cli find "Add" --filename=results.md
playwright-cli eval "document.title"
playwright-cli eval "el => el.textContent" e5
# get element id, class, or any attribute not visible in the snapshot
playwright-cli eval "el => el.id" e5
playwright-cli eval "el => el.getAttribute('data-testid')" e5
playwright-cli dialog-accept
playwright-cli dialog-accept "confirmation text"
playwright-cli dialog-dismiss
playwright-cli resize 1920 1080
playwright-cli close
```

### Navigation

```bash
playwright-cli go-back
playwright-cli go-forward
playwright-cli reload
```

### Keyboard

```bash
playwright-cli press Enter
playwright-cli press ArrowDown
playwright-cli keydown Shift
playwright-cli keyup Shift
```

### Mouse

```bash
playwright-cli mousemove 150 300
playwright-cli mousedown
playwright-cli mousedown right
playwright-cli mouseup
playwright-cli mouseup right
# scroll by <dx> <dy> pixels, negative dy scrolls up
# the element under the mouse pointer scrolls, so mousemove over it first
playwright-cli mousewheel 0 100
playwright-cli mousewheel 0 -100
```

### Save as

```bash
playwright-cli screenshot
playwright-cli screenshot e5
playwright-cli screenshot --filename=page.png
playwright-cli screenshot --hires
playwright-cli pdf --filename=page.pdf
```

### Tabs

```bash
playwright-cli tab-list
playwright-cli tab-new
playwright-cli tab-new "$E2E_BASE_URL/page"
playwright-cli tab-new "$E2E_BASE_URL/page" --isolated-context=user-b
playwright-cli tab-close
playwright-cli tab-close 2
playwright-cli tab-select 0
```

### Storage

```bash
# state files contain tokens: keep them under .playwright-cli/, never commit, delete after use
playwright-cli state-save .playwright-cli/auth.json
playwright-cli state-load .playwright-cli/auth.json

# Cookies
playwright-cli cookie-list
playwright-cli cookie-list --domain=localhost
playwright-cli cookie-delete session_id
playwright-cli cookie-clear

# LocalStorage
playwright-cli localstorage-list
playwright-cli localstorage-get theme
playwright-cli localstorage-set theme dark
playwright-cli localstorage-delete theme
playwright-cli localstorage-clear

# SessionStorage
playwright-cli sessionstorage-list
playwright-cli sessionstorage-get step
playwright-cli sessionstorage-set step 3
playwright-cli sessionstorage-delete step
playwright-cli sessionstorage-clear
```

### Emulation

```bash
playwright-cli set-color-scheme dark
playwright-cli clear-color-scheme
playwright-cli set-reduced-motion reduce
playwright-cli clear-reduced-motion
playwright-cli set-forced-colors active
playwright-cli clear-forced-colors
playwright-cli set-contrast more
playwright-cli clear-contrast
playwright-cli set-media print
playwright-cli clear-media
```

### Network

```bash
playwright-cli route "**/*.jpg" --status=404
playwright-cli route "**/api/documents" --body='{"mock": true}'
playwright-cli route-list
playwright-cli unroute "**/*.jpg"
playwright-cli unroute
```

### DevTools

```bash
playwright-cli console
playwright-cli console warning
playwright-cli requests
playwright-cli request 5
# run-code executes arbitrary code in the browser context: only run code you wrote or reviewed
playwright-cli run-code --filename=script.js
playwright-cli tracing-start
playwright-cli tracing-stop

# record user actions in the browser, print them as Playwright code on stop
playwright-cli recording-start
playwright-cli recording-stop

# generate a Playwright locator for an element from its ref or selector
playwright-cli generate-locator e5 --raw

# show a persistent highlight overlay for an element, optionally with a custom style
playwright-cli highlight e5
playwright-cli highlight e5 --style="outline: 3px dashed red"
# hide a single element highlight, or all page highlights when no target is given
playwright-cli highlight e5 --hide
playwright-cli highlight --hide
```

## Raw output

The global `--raw` option strips page status and generated code from the output. It keeps the result value, errors, and the page snapshot (or the link to the snapshot file). Use it to pipe command output into other tools. Commands that don't produce output return nothing.

```bash
playwright-cli --raw eval "JSON.stringify(performance.timing)" | jq '.loadEventEnd - .navigationStart'
playwright-cli --raw eval "JSON.stringify([...document.querySelectorAll('a')].map(a => a.href))" > links.json
playwright-cli --raw snapshot > before.yml
playwright-cli click e5
playwright-cli --raw snapshot > after.yml
diff before.yml after.yml
playwright-cli --raw localstorage-get theme
```

For structured output wrapping every reply as JSON, pass --json
```bash
playwright-cli list --json
```

## Open parameters
```bash
# Headless is the default; add --headed only when the user asks
# Use specific browser when creating session (browsers must already be installed)
playwright-cli open --browser=chromium
playwright-cli open --browser=firefox
playwright-cli open --browser=webkit

# Emulate a generic mobile device (Pixel 10 for Chromium, iPhone 17 for WebKit).
# Prefer this when a mobile layout is acceptable: mobile pages are usually
# lighter, so snapshots are smaller and cheaper.
playwright-cli open --mobile
playwright-cli open --device="iPhone 15"

# Use persistent profile (by default profile is in-memory)
playwright-cli open --persistent
# persistent profiles keep cookies/tokens on disk: delete with delete-data when done

# Start with config file
playwright-cli open --config=my-config.json

# Close the browser
playwright-cli close
# Delete user data for the default session
playwright-cli delete-data
```

## Snapshots

After each command, playwright-cli provides a snapshot of the current browser state.

```bash
> playwright-cli goto "$E2E_BASE_URL"
### Page
- Page URL: http://localhost:8080/
- Page Title: Chat With Your Docs
### Snapshot
[Snapshot](.playwright-cli/page-2026-02-14T19-22-42-679Z.yml)
```

You can also take a snapshot on demand using `playwright-cli snapshot` command. All the options below can be combined as needed.

```bash
# default - save to a file with timestamp-based name
playwright-cli snapshot

# save to file, use when snapshot is a part of the workflow result
playwright-cli snapshot --filename=after-click.yaml

# snapshot an element instead of the whole page
playwright-cli snapshot "#main"

# limit snapshot depth for efficiency, take a partial snapshot afterwards
playwright-cli snapshot --depth=4
playwright-cli snapshot e34

# include each element's bounding box as [box=x,y,width,height]
playwright-cli snapshot --boxes

# search a large snapshot instead of capturing it all — returns matching nodes
# with 3 lines of context around each match (like grep -C)
playwright-cli find "Add to cart"
playwright-cli find --regex "\\$[0-9]+\\.[0-9]{2}"
```

## Targeting elements

By default, use refs from the snapshot to interact with page elements.

```bash
# get snapshot with refs
playwright-cli snapshot

# interact using a ref
playwright-cli click e15
```

You can also use css selectors or Playwright locators.

```bash
# css selector
playwright-cli click "#main > button.submit"

# role locator
playwright-cli click "getByRole('button', { name: 'Submit' })"

# test id
playwright-cli click "getByTestId('submit-button')"
```

## Browser Sessions

```bash
# create new browser session named "mysession" with persistent profile
playwright-cli -s=mysession open "$E2E_BASE_URL" --persistent
playwright-cli -s=mysession click e6
playwright-cli -s=mysession close  # stop a named browser
playwright-cli -s=mysession delete-data  # delete user data for persistent session

playwright-cli list
# Close all browsers
playwright-cli close-all
# Forcefully kill all browser processes
playwright-cli kill-all
```

## Installation

Never install packages or browsers without asking the user first. Use the locally pinned version:

```bash
npx --no-install playwright --version   # needs Playwright 1.59 or newer
npx --no-install playwright cli --help
```

If it is not available, stop and ask the user whether to add or upgrade `@playwright/test` (do not run `npm install -g ...@latest`).

## Example: Form submission

```bash
playwright-cli open "$E2E_BASE_URL/login"
playwright-cli snapshot

# credentials come from env/fixtures, never literals
playwright-cli fill e1 "$E2E_USER"
playwright-cli fill e2 "$E2E_PASSWORD"
playwright-cli click e3
playwright-cli snapshot
playwright-cli close
```

## Example: Multi-tab workflow

```bash
playwright-cli open "$E2E_BASE_URL"
playwright-cli tab-new "$E2E_BASE_URL/other"
playwright-cli tab-list
playwright-cli tab-select 0
playwright-cli snapshot
playwright-cli close
```

## Example: Debugging with DevTools

```bash
playwright-cli open "$E2E_BASE_URL"
playwright-cli click e4
playwright-cli fill e7 "test"
playwright-cli console
playwright-cli requests
playwright-cli close
```

```bash
# traces include headers and bodies (tokens): delete after use
playwright-cli open "$E2E_BASE_URL"
playwright-cli tracing-start
playwright-cli click e4
playwright-cli fill e7 "test"
playwright-cli tracing-stop
playwright-cli close
```

## Specific tasks

* **Running and Debugging Playwright tests** [references/playwright-tests.md](references/playwright-tests.md)
* **Request mocking** [references/request-mocking.md](references/request-mocking.md)
* **Running Playwright code** [references/running-code.md](references/running-code.md)
* **Browser session management** [references/session-management.md](references/session-management.md)
* **Storage state (cookies, localStorage)** [references/storage-state.md](references/storage-state.md)
* **Test generation (plan / generate / heal)** [references/test-generation.md](references/test-generation.md)
* **Tracing** [references/tracing.md](references/tracing.md)
* **Inspecting element attributes** [references/element-attributes.md](references/element-attributes.md)
