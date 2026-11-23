# Language-Specific Security Quirks

> **Important:** The examples below are illustrative starting points, not exhaustive. When reviewing code, think like a senior security researcher: consider the language's memory model, type system, standard library pitfalls, ecosystem-specific attack vectors, and historical CVE patterns. Each language has deeper quirks beyond what's listed here.

Different languages have unique security pitfalls. This trimmed copy keeps the languages this project uses (see the provenance note in `../LICENSE`). **Go deeper for the specific language you're working in.**

## Contents
- [JavaScript / TypeScript](#javascript--typescript)
- [Python](#python)
- [Shell (Bash)](#shell-bash)
- [SQL (All Dialects)](#sql-all-dialects)

---

### JavaScript / TypeScript
**Main Risks:** Prototype pollution, XSS, eval injection
```javascript
// UNSAFE: Prototype pollution - the vector is RECURSIVE merge, not a shallow copy.
// Payload {"__proto__": {"isAdmin": true}} reaches Object.prototype for every object.
deepMerge(config, JSON.parse(body))   // hand-rolled recursive merges; also lodash.merge / _.set
                                      // on old Lodash (CVE-2018-3721, CVE-2018-16487, CVE-2020-8203).
                                      // Current 4.17.x+ filters __proto__ and constructor.prototype:
                                      // check the lockfile before flagging a Lodash call.
// SAFE: skip the dangerous keys at every depth (stripping only the top level misses
// {"a": {"__proto__": ...}}), or validate against a schema before merging
const BLOCKED = new Set(["__proto__", "constructor", "prototype"]);
function safeMerge(target, src) {
  for (const k of Object.keys(src)) {
    if (BLOCKED.has(k)) continue;
    const v = src[k];
    if (v && typeof v === "object" && !Array.isArray(v)) {
      const cur = Object.hasOwn(target, k) ? target[k] : undefined;
      if (!cur || typeof cur !== "object" || Array.isArray(cur)) target[k] = {};
      safeMerge(target[k], v);
    } else {
      target[k] = v;
    }
  }
  return target;
}

// UNSAFE: eval injection (and its aliases)
eval(userCode); new Function(userCode); setTimeout(userCode, 0);
// SAFE: Never build executable code from user input
```
**Watch for:** `eval()`, `new Function()`, string arguments to `setTimeout`/`setInterval`,
`innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write()`, `dangerouslySetInnerHTML`,
`location`/`href` assignment from user input, `__proto__` and `constructor.prototype`,
`postMessage` handlers without an `origin` check.

---

### Python
**Main Risks:** Pickle deserialization, format string injection, SQL/shell injection
```python
# UNSAFE: Pickle RCE
pickle.loads(user_data)
# SAFE: Use JSON or validate source
json.loads(user_data)

# UNSAFE: SQL injection via string interpolation
query = "SELECT * FROM users WHERE name = '%s'" % user_input
# SAFE: Parameterized
cursor.execute("SELECT * FROM users WHERE name = %s", (user_input,))

# UNSAFE: Format string injection - user controls the TEMPLATE, not the argument.
# "{u.__class__.__init__.__globals__[SECRET]}" walks attributes and leaks module globals.
user_template.format(u=user)
# SAFE: template is a literal, user data is an argument
"Hello {name}".format(name=user_input)
```
**Watch for:** `pickle`, `yaml.load` without `SafeLoader`, `eval()`, `exec()`, `os.system()`,
`subprocess` with `shell=True`, user-controlled format templates, `jinja2.Template(user_input)`
(SSTI), `__import__`

---

### Shell (Bash)
**Main Risks:** Command injection, word splitting, globbing
```bash
# UNSAFE: Unquoted variables
rm $user_file
# SAFE: Always quote
rm "$user_file"

# UNSAFE: eval
eval "$user_command"
# SAFE: Never eval user input
```
**Watch for:** Unquoted variables, `eval`, backticks, `$(...)` with user input, missing `set -euo pipefail`

---

### SQL (All Dialects)
**Main Risks:** Injection, privilege escalation, data exfiltration
```sql
-- UNSAFE: String concatenation
"SELECT * FROM users WHERE id = " + userId

-- SAFE: Parameterized query (language-specific)
-- Use prepared statements in ALL cases
```
**Watch for:** Dynamic SQL, `EXECUTE IMMEDIATE`, stored procedures with dynamic queries, privilege grants
