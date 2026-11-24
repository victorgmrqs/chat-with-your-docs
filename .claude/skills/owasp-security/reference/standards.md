# OWASP Agentic Top 10 and ASVS 5.0

> Moved unchanged from `SKILL.md` (see `../SOURCE.md`).

## OWASP Top 10 for Agentic Applications (2026)

For AI agent systems that plan, call tools, or keep memory:

| Risk | Description | Mitigation |
|------|-------------|------------|
| ASI01: Agent Goal Hijack | Prompt injection alters agent objectives | Treat tool and retrieved content as data, goal boundaries, behavioral monitoring |
| ASI02: Tool Misuse & Exploitation | Tools used in unintended ways | Least privilege, fine-grained permissions, validate I/O |
| ASI03: Identity & Privilege Abuse | Delegated trust, inherited credentials, role chain exploits | Short-lived scoped tokens, identity verification |
| ASI04: Agentic Supply Chain Vulnerabilities | Compromised plugins/MCP servers | Verify signatures, sandbox, allowlist plugins |
| ASI05: Unexpected Code Execution | Unsafe code generation/execution | Sandbox execution, static analysis, human approval |
| ASI06: Memory & Context Poisoning | Corrupted RAG/context data | Validate stored content, segment by trust level |
| ASI07: Insecure Inter-Agent Communication | Spoofing/intercepting agent-to-agent messages | Authenticate, encrypt, verify message integrity |
| ASI08: Cascading Failures | Errors propagate across systems | Circuit breakers, graceful degradation, isolation |
| ASI09: Human-Agent Trust Exploitation | Over-trust in agents leveraged to manipulate users | Label AI content, user education, verification steps |
| ASI10: Rogue Agents | Compromised agents acting maliciously | Behavior monitoring, kill switches, anomaly detection |

## ASVS 5.0 Key Requirements

ASVS 5.0 (May 2025) renumbered and reorganized every chapter. **4.0 requirement IDs do not
map to 5.0** — `V2.1.1` meant "password length" in 4.0 and means something else now. Cite
5.0 IDs only. Levels are defined by share of requirements, not by application category:

| Level | Share | Intent |
|---|---|---|
| L1 | ~20% | Minimum bar; deliberately small to lower the barrier to entry |
| L2 | ~50% (≈70% cumulative) | What most applications should target |
| L3 | remaining ~30% | Highest assurance |

### Level 1 — the minimum bar
- Passwords **at least 8 characters**; 15+ strongly recommended (6.2.1)
- No composition rules — permit any characters, paste, and password managers (6.2.5, 6.2.7)
- Block at least the top 3000 common passwords (6.2.4)
- Anti-automation against credential stuffing and brute force (6.3.1)
- No default accounts like `root`/`admin`/`sa` (6.3.2)
- Reference session tokens from a CSPRNG with 128+ bits entropy (7.2.3)
- New session token issued on authentication and re-authentication (7.2.4)
- Session fully unusable after logout or expiry (7.4.1)
- Function-level and data-level access restricted to explicit permissions (8.2.1, 8.2.2)
- Authorization enforced at a trusted service layer the client cannot manipulate (8.3.1)
- Parameterized queries / ORM for all data access (1.2.4); parameterized OS calls (1.2.5)
- Context-appropriate output encoding for HTML, URLs, and JavaScript/JSON (1.2.1–1.2.3)
- Avoid `eval()` and dynamic code execution (1.3.2)
- Input validated at a trusted service layer, positive/allowlist where possible (2.2.1, 2.2.2)
- TLS 1.2+ on all external traffic, publicly trusted certificates (12.1.1, 12.2.1, 12.2.2)
- Approved ciphers and modes only — no ECB, no PKCS#1 v1.5 padding (11.3.1, 11.3.2)
- No sensitive data in URLs or query strings (14.2.1)

### Level 2 — what most applications should target
- MFA, or a documented combination of single factors (6.3.3)
- Passwords checked against a breached-password set (6.2.12)
- No forced periodic password rotation — rotate only on compromise (6.2.10)
- **All security logging starts here.** ASVS 5.0 has *no* L1 logging requirements; the whole
  of V16 is L2+. Log authentication attempts, failed authorization, security events, and
  unexpected errors (16.3.1–16.3.4)
- Log entries carry when/where/who/what metadata on a synchronized clock (16.2.1, 16.2.2)
- Logs encoded against log injection, protected from modification, shipped off-box (16.4.1–16.4.3)
- Generic error message to the user; detail stays in the log (16.5.1)

### Level 3 — highest assurance

ASVS 5.0 has **92 L3 requirements**; they are not enumerated here. Two worth knowing because
they tighten an L2 requirement rather than adding a new one:

- One factor must be hardware-based and phishing-resistant, e.g. a FIDO key (6.3.3, L3 clause)
- Log **all** authorization decisions, not only failures (16.3.2, L3 clause)

For an actual L3 assessment, work from the standard itself (OWASP ASVS 5.0).
