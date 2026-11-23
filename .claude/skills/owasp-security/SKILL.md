---
name: owasp-security
description: Reviews code for security vulnerabilities and guides secure implementation using OWASP Top 10:2025, ASVS 5.0, the OWASP Top 10 for LLM Applications (2026), and the OWASP Top 10 for Agentic Applications (2026). Use when reviewing code or a diff for security issues, implementing authentication, authorization, sessions, or cryptography, handling untrusted input, files, or URLs, hardening config, dependencies, or CI, or building LLM and AI agent features.
when_to_use: Trigger phrases include "security review", "security check", "anything exploitable", "audit this", "is this secure", "is this safe to ship", "check for vulnerabilities", "find security bugs", "threat model", "OWASP", "ASVS", "CWE", "prompt injection", and "MCP server security".
license: MIT
---

## Project overrides (Chat With Your Docs)

These project rules win over anything below (see `CLAUDE.md`, "Rules and skills").

- Stack in scope: FastAPI + LangChain backend (Python), React + Vite SPA (TypeScript), nginx,
  PostgreSQL + pgvector, Docker Compose. Ignore checklist items for stacks the change does not
  touch.
- Project rules come first: `.claude/rules/security-nginx.md`, `security-uploads.md` and
  `security-llm.md`, plus `docs/domain-context.md` (DOM-xx). A finding that contradicts a DOM
  rule is reported as a rule conflict, not fixed silently.
- Read and report only: when a check needs a tool or a URL, recommend the command instead of
  running it. The `CLAUDE.md` non-negotiables (no installs or one-off tools, no content or
  secrets in output) apply to findings too.

# OWASP Security

Apply these standards when writing or reviewing code. For a review, follow the workflow below.

**Reference files** (read the one the task needs, and only the section you need):
- [`reference/review-checklist.md`](reference/review-checklist.md): coverage checklist for every Top 10 category, plus LLM and agent checks. Read during step 3 of a review.
- [`reference/languages.md`](reference/languages.md): per-language pitfalls with unsafe/safe examples for TypeScript, Python, Shell and SQL (trimmed to this project's languages). Read the section for the language under review.
- [`reference/config-and-supply-chain.md`](reference/config-and-supply-chain.md): A02 and A03 in Dockerfiles, framework config, security headers, lockfiles, and CI/CD. Read when the change touches config, Dockerfiles, dependencies, or pipelines (Kubernetes and Terraform sections were not vendored).

## Security Review Workflow

Copy this checklist into your response and tick it off as you go:

```
Security Review Progress:
- [ ] Step 1: Map entry points and trust boundaries
- [ ] Step 2: Load the references this code needs
- [ ] Step 3: Sweep for candidate issues
- [ ] Step 4: Triage every candidate
- [ ] Step 5: Report findings
```

**Step 1: Map entry points and trust boundaries.** List where attacker-controlled data enters:
routes and handlers, headers and cookies, uploads, webhooks, queue consumers, CLI arguments,
third-party API responses, and anything an LLM reads or returns. Note where authentication and
authorization are enforced; it is often centralized in middleware rather than per route.

**Step 2: Load the references this code needs.** The language section of `languages.md`;
`config-and-supply-chain.md` if config, Dockerfiles, dependencies, or CI changed; the "LLM and Agent
Features" section of `review-checklist.md` and `.claude/rules/security-llm.md` if the code calls a model.

**Step 3: Sweep for candidate issues.** Walk `review-checklist.md` for the categories the code
touches. For each candidate, trace the path from an entry point in step 1 to the sink.

**Step 4: Triage every candidate** with the rubric in "Before Reporting a Finding" below. Drop
candidates that fail it, or downgrade them to defense-in-depth. If a candidate's reachability
is unclear, go back to step 1 for that input before deciding.

**Step 5: Report findings** in the format below, highest severity first.

## Before Reporting a Finding

A pattern match is not a vulnerability. The most common failure mode in automated security
review is reporting unreachable or already-mitigated code, which buries the real findings.
Confirm all four before reporting:

1. **Is the input actually attacker-controlled?** Trace it back to a real entry point: a
   request parameter, header, cookie, uploaded file, webhook, queue message, or third-party
   API response. A value that only ever comes from a constant, an enum, or trusted internal
   config is not an injection source.
2. **Is the sink reachable with that input?** Check whether validation, an allowlist, an ORM,
   or a framework-level control already sits between them. Look for auth dependencies
   (FastAPI `Depends`, router-level dependencies, middleware) before flagging a route as missing authorization. Enforcement is often
   centralized rather than per-route.
3. **What is the blast radius?** Who can trigger it, what do they get, and does it cross a
   trust boundary? An SSRF reaching cloud metadata differs from one reaching localhost only.
4. **Can the attacker perform every step?** Each step of the exploit must be possible from
   the attacker's position. A symlink race needs a way to create symlinks on the server; a
   header attack needs a client that can set that header. If a step needs a capability the
   code doesn't show the attacker having, the finding is "Needs verification", not High.

Report severity by exploitability, not by pattern. State the concrete path (*this input
reaches this sink*) and say so explicitly when a finding is theoretical or defense-in-depth
rather than directly exploitable. If reachability can't be determined from the code available,
say that instead of asserting either way.

## Reporting Format

One block per finding, highest severity first:

```
[SEVERITY] Title (CWE-###, OWASP A##:2025, LLM## Risk Name, ASI## Risk Name)
Location:   path/to/file.ext:LINE
Path:       <entry point> -> <intermediate hops> -> <sink>
Impact:     who can trigger it, what they get, which trust boundary it crosses
Fix:        the concrete change, with a code snippet when it isn't obvious
Confidence: Confirmed | Likely | Needs verification (say what you couldn't see)
```

Write every LLM and ASI ID with its risk name, e.g. "LLM03 Excessive Agency". A bare LLM ID is
ambiguous: the 2025 and 2026 editions use the same numbers for different risks.

| Severity | Meaning |
|---|---|
| Critical | Unauthenticated remote code execution, auth bypass, or mass data exposure |
| High | Authenticated exploitation crossing a trust boundary (IDOR into other tenants, SQLi behind login) |
| Medium | Needs unusual preconditions, or impact is limited to the attacker's own data |
| Low | Defense-in-depth gap with no demonstrated exploit path |
| Info | Hardening suggestion; say plainly that it is not a vulnerability |

If the review finds nothing exploitable, say so directly. Do not pad the report with Info items
to look thorough; a long list is what makes real findings get ignored.

## OWASP Top 10:2025

Three categories were renamed from 2021 and two are new (A03, A10). Use these names and
numbers; much OWASP material online still cites the 2021 list.

| # | Category | Key Prevention |
|---|----------|----------------|
| A01 | Broken Access Control (now includes SSRF) | Deny by default, enforce server-side, verify ownership |
| A02 | Security Misconfiguration | Harden configs, disable defaults, minimize features |
| A03 | Software Supply Chain Failures | Lock versions, verify integrity, audit dependencies |
| A04 | Cryptographic Failures | TLS 1.2+, AES-256-GCM, Argon2/bcrypt for passwords |
| A05 | Injection | Parameterized queries, input validation, safe APIs |
| A06 | Insecure Design | Threat model, rate limit, design security controls |
| A07 | Authentication Failures | MFA, check breached passwords, secure sessions |
| A08 | Software or Data Integrity Failures | Sign packages, SRI for CDN, safe serialization |
| A09 | Security Logging and Alerting Failures | Log security events, structured format, alerting |
| A10 | Mishandling of Exceptional Conditions | Fail-closed, hide internals, log with context |

## OWASP Top 10 for LLM Applications (2026)

For applications that call LLMs (chatbots, RAG, copilots, agents). The 2026 edition renumbered
the list; cite 2026 IDs only, or name the risk.

| # | Risk | Key Mitigation |
|---|------|----------------|
| LLM01 | Prompt Injection | No complete fix exists. Fence untrusted content (including images, audio, tool output), keep privileges out of the model's reach, filter outputs |
| LLM02 | Sensitive Information Disclosure | Sanitize training/RAG data, strip PII from context, restrict what the model can retrieve per user |
| LLM03 | Excessive Agency | Minimize tools and permissions, require human approval for destructive actions, scope credentials per task |
| LLM04 | Supply Chain | Verify model provenance and signatures, vet third-party model hubs, lock model + adapter versions |
| LLM05 | Data and Model Poisoning | Validate training/fine-tuning sources, anomaly-detect on data ingestion, hold-out integrity tests |
| LLM06 | Unbounded Consumption | Rate-limit per user/key, cap tokens and tool calls per request, monitor cost, set hard timeouts |
| LLM07 | Misinformation | Cite sources, surface confidence, require grounding for high-stakes answers, disclose AI provenance |
| LLM08 | Hidden Context Exposure | Assume the system prompt, tool schemas, and other hidden context are extractable: no secrets there, and no authorization or policy that relies on them staying hidden |
| LLM09 | Vector and Embedding Weaknesses | Tenant-isolate vector stores, access-control on retrieval, sign or hash chunks against indirect prompt injection |
| LLM10 | Improper Output Handling | Treat all LLM output, including generated code, as untrusted input: validate, escape, or sandbox before any sink (SQL, shell, HTML, code, tool calls) |

## Agentic Top 10 and ASVS 5.0

Read [`reference/standards.md`](reference/standards.md) when the change adds authentication,
sessions, agents or tool calling.
