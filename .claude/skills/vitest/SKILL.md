---
name: vitest
description: Vitest unit and integration tests for the React + Vite frontend (jsdom, Testing Library, MSW): test API, expect, hooks, mocking with vi, snapshots, coverage, filtering, fixtures. Use only for tests run by Vitest. Not for Playwright E2E tests and not for backend pytest.
license: MIT
metadata:
  author: Anthony Fu
  version: "2026.10.23"
  source: Adapted from https://github.com/antfu/skills (skills/vitest), see SOURCE.md
---

# Vitest

## Project overrides

These rules come from the project and win over anything below.

- Frontend tests use Vitest + Testing Library (jsdom environment) + MSW. E2E tests are Playwright (see the `playwright-cli` skill), never Vitest Browser Mode.
- HTTP is mocked with MSW at the network boundary. Never `vi.stubGlobal('fetch', ...)` or `vi.spyOn(globalThis, 'fetch')`. See the MSW section in [features-mocking](references/features-mocking.md).
- Query the DOM the way users do: `screen.getByRole(...)` first (see the Testing Library section in [features-mocking](references/features-mocking.md)).
- TDD in vertical slices: red, green, refactor at every green (see the `tdd` skill).
- Exact Vitest/Vite versions are chosen when the frontend is scaffolded. This skill was written against Vitest 5.1.0-beta.1: verify against the version in `frontend/package.json` before relying on any v5-only behaviour. v5-only items in these references:
  - `clearMocks` defaults to `true`; `describe.sequential`/`test.sequential` removed (use `{ concurrent: false }`)
  - `poolOptions` removed (top-level `maxWorkers`), default pool `forks`, `workspace` removed in favour of `projects`
  - `vi.mock`/`vi.unmock`/`vi.hoisted` must be top-level; class mocks keep prototype methods
  - `coverage.all`/`coverage.extensions` removed; `.vitest/` artifact directory; requires Vite >= 6.4.0 and Node >= 22.12.0
  - `list` parses files statically; `cache` option, `--since-last-run` and other v5.1 additions

Vitest is a testing framework powered by Vite with a Jest-compatible API, native ESM and TypeScript, and it shares the Vite config, resolvers and plugins of the app.

## Core

| Topic | Description | Reference |
|-------|-------------|-----------|
| Configuration | Vitest and Vite config integration, defineConfig usage | [core-config](references/core-config.md) |
| CLI | Command line interface, commands and options | [core-cli](references/core-cli.md) |
| Test API | test/it function, modifiers like skip, only, concurrent | [core-test-api](references/core-test-api.md) |
| Describe API | describe/suite for grouping tests and nested suites | [core-describe](references/core-describe.md) |
| Expect API | Assertions with toBe, toEqual, matchers and asymmetric matchers | [core-expect](references/core-expect.md) |
| Hooks | beforeEach, afterEach, beforeAll, afterAll, aroundEach | [core-hooks](references/core-hooks.md) |

## Features

| Topic | Description | Reference |
|-------|-------------|-----------|
| Mocking | vi mocks, modules, timers, dates, MSW for HTTP, Testing Library pointer | [features-mocking](references/features-mocking.md) |
| Snapshots | Snapshot testing with toMatchSnapshot and inline snapshots | [features-snapshots](references/features-snapshots.md) |
| Coverage | Code coverage with V8 or Istanbul providers | [features-coverage](references/features-coverage.md) |
| Test Context | Test fixtures, context.expect, test.extend for custom fixtures | [features-context](references/features-context.md) |
| Filtering | Filter tests by name and file patterns | [features-filtering](references/features-filtering.md) |

## Advanced

| Topic | Description | Reference |
|-------|-------------|-----------|
| Vi Utilities | vi helper: mock, spyOn, fake timers, hoisted, waitFor | [advanced-vi](references/advanced-vi.md) |
| Environments | The jsdom test environment | [advanced-environments](references/advanced-environments.md) |
| Type Testing | Type-level testing with expectTypeOf and assertType | [advanced-type-testing](references/advanced-type-testing.md) |
