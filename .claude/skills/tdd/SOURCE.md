# Source

- Upstream: https://github.com/mattpocock/skills
- Path: `skills/engineering/tdd`
- Commit: abeeaf95660ba9e8b7c753eb38f441ca707a8823
- License: MIT (see `LICENSE`)
- Vendored: 2026-11-20
- Modified: yes

## Modifications

- Frontmatter: `description` no longer mentions integration tests; added `license`.
- Added "Project overrides" section (real PostgreSQL, at most 3 mocks, MSW on the frontend, ask before installing).
- SKILL.md: loop is red, green, refactor with refactor at every green (upstream excluded refactoring); removed references to the `codebase-design` and `code-review` skills; seams are confirmed once per feature.
- mocking.md: rewritten boundary list (never mock the database; mocked boundaries are LLM/embedding providers via declared fakes, time, external HTTP via MSW); added pytest examples.
- tests.md: added pytest examples next to the TypeScript ones; `jest.mock` changed to `vi.mock`.

## Dropped files

`agents/openai.yaml`.
