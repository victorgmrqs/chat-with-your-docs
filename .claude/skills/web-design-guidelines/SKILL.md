---
name: web-design-guidelines
description: Review UI code in this React + Vite SPA for Web Interface Guidelines compliance (accessibility, focus states, forms, animation, typography, touch). Use when asked to "review my UI", "check accessibility", "audit design" or "review UX". Review-only; does not generate UI.
metadata:
  author: vercel
  version: "1.1.0"
  argument-hint: <file-or-pattern>
---

## Project overrides

These project rules win over the guidelines below:

- The app is a client-only React + Vite SPA with Tailwind v4 and shadcn/ui on Radix. Rules about SSR or hydration do not apply.
- Light theme only. Do not recommend dark mode, `color-scheme: dark` or dark variants.
- Colors come from semantic design tokens (HEX). Flag hardcoded colors and Tailwind palette classes; never suggest them as fixes.
- Red is reserved for failures.
- Prefer the project's shadcn/ui components over custom markup when suggesting fixes.
- Do not fetch anything from the network. Do not run scripts or install packages.
- Findings and any suggested copy are in English.

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines.

## How It Works

1. Read the bundled guidelines at [references/command.md](references/command.md)
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in the guidelines
4. Output findings in the terse `file:line` format

## Guidelines Source

The rules are bundled with this skill in the [references/command.md](references/command.md) file. Read that file before each review. Do not fetch rules from the network.

The bundled file is derived from the upstream snapshot at https://github.com/vercel-labs/web-interface-guidelines (commit 434b7f91364665f2f733b310ec54809bf8f37937) with project edits listed in `SOURCE.md`, so it no longer matches the upstream SHA-256.

The file contains all the rules and output format instructions.
Where it says `$ARGUMENTS`, use the files or pattern the user asked to review.

## Usage

When a user provides a file or pattern argument:
1. Read [references/command.md](references/command.md)
2. Read the specified files
3. Apply all rules from the guidelines
4. Output findings using the format specified in the guidelines

If no files specified, ask the user which files to review.
