# shadcn CLI Reference

Configuration is read from `components.json`.

> **IMPORTANT:** Never run a CLI command yourself. Propose the exact command to the user and wait for confirmation. Use the pinned version recorded in `frontend/package.json` (`shadcn@<pinned>` below), never `@latest`, and use the project's package runner (`npx`, `pnpm dlx`, ... based on `packageManager`). Never install packages without asking.

> **IMPORTANT:** Only use the flags documented below. Do not invent or guess flags. If a flag isn't listed here, it doesn't exist.

> **Scope:** this project uses the official `@shadcn` registry only. Community registries, URL or `owner/repo` items, presets, `apply`, `init --force`, `--all` and monorepo scaffolding are out of scope. The project is already initialized, so `init` is not needed.

## Contents

- Commands: add (dry-run, smart merge), search, view, info

---

## Commands

### `add` - Add components

> **IMPORTANT:** To compare local components against upstream or to preview changes, ALWAYS use `npx shadcn@<pinned> add <component> --dry-run`, `--diff`, or `--view`. NEVER fetch raw files from GitHub or other sources manually.

```bash
npx shadcn@<pinned> add [components...] [options]
```

Accepts official component names (`button`) or `@shadcn/<name>`.

| Flag            | Short | Description                                                                                                          | Default |
| --------------- | ----- | -------------------------------------------------------------------------------------------------------------------- | ------- |
| `--overwrite`   | `-o`  | Overwrite existing files (only with explicit user approval)                                                          | `false` |
| `--cwd <cwd>`   | `-c`  | Working directory                                                                                                    | current |
| `--path <path>` | `-p`  | Target path for the component                                                                                        | -       |
| `--dry-run`     |       | Preview all changes without writing files                                                                            | `false` |
| `--diff [path]` |       | Show diffs. Without a path, shows the first 5 files. With a path, shows that file only (implies `--dry-run`)         | -       |
| `--view [path]` |       | Show file contents. Without a path, shows the first 5 files. With a path, shows that file only (implies `--dry-run`) | -       |

Do not pass `-y` or `--all`. The user confirms each add interactively.

#### Dry-Run Mode

Use `--dry-run` to preview what `add` would do without writing any files. `--diff` and `--view` both imply `--dry-run`.

```bash
# Preview all changes.
npx shadcn@<pinned> add button --dry-run

# Show the diff for a specific file.
npx shadcn@<pinned> add button --diff button.tsx

# Show the full content of a specific file.
npx shadcn@<pinned> add button --view button.tsx

# CSS diffs.
npx shadcn@<pinned> add button --diff globals.css
```

**When to use dry-run:**

- When the user asks "what files will this add?" or "what will this change?"
- Before overwriting existing components, use `--diff` to preview the changes first.
- When checking what CSS changes would be made to the global CSS file.

#### Smart Merge from Upstream

See [Updating Components in SKILL.md](./SKILL.md#updating-components) for the full workflow.

### `search` - Search the official registry

```bash
npx shadcn@<pinned> search @shadcn [options]
```

Fuzzy search. Without `-q`, lists all items.

| Flag                | Short | Description                                                       | Default |
| ------------------- | ----- | ----------------------------------------------------------------- | ------- |
| `--query <query>`   | `-q`  | Search query                                                      | -       |
| `--type <type>`     | `-t`  | Filter by item type (e.g. `ui`, `block`, `hook`); comma-separated | -       |
| `--limit <number>`  | `-l`  | Max items to display                                              | `100`   |
| `--offset <number>` | `-o`  | Items to skip                                                     | `0`     |
| `--json`            |       | Output as JSON                                                    | `false` |
| `--cwd <cwd>`       | `-c`  | Working directory                                                 | current |

### `view` - View item details

```bash
npx shadcn@<pinned> view @shadcn/<item>
```

Displays registry item info including file contents. Prefer `add --dry-run/--diff/--view` when the user wants to preview changes to their project; `view` only shows raw registry metadata.

### `diff` - Check for updates

Do not use this command. Use `npx shadcn@<pinned> add --diff` instead.

### `info` - Project information

```bash
npx shadcn@<pinned> info [options]
```

Displays project info and `components.json` configuration (aliases, Tailwind version, resolved paths). Reading `components.json` directly gives the same data without running anything.

| Flag          | Short | Description       | Default |
| ------------- | ----- | ----------------- | ------- |
| `--cwd <cwd>` | `-c`  | Working directory | current |

**Components.json fields:**

| Field                | Type     | Meaning                                                                                    |
| -------------------- | -------- | ------------------------------------------------------------------------------------------ |
| `base`               | `string` | Primitive library. Must be `radix` in this project                                         |
| `style`              | `string` | Visual style                                                                               |
| `tailwind.css`       | `string` | Global CSS path - this is where custom CSS variables go                                    |
| `iconLibrary`        | `string` | Icon library - determines icon import package (e.g. `lucide-react`)                        |
| `aliases.components` | `string` | Component import alias (e.g. `@/components`)                                               |
| `aliases.utils`      | `string` | Utils import alias (e.g. `@/lib/utils`)                                                    |
| `aliases.ui`         | `string` | UI component alias (e.g. `@/components/ui`)                                                |
| `aliases.lib`        | `string` | Lib alias (e.g. `@/lib`)                                                                   |
| `aliases.hooks`      | `string` | Hooks alias (e.g. `@/hooks`)                                                               |
