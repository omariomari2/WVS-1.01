# Security Considerations

## This Is the Most Important Section

If this presentation is for a product security manager, this section matters more than anything else.

Why?

Because this project is a security product.

That means it has two jobs:

1. detect security issues in other systems
2. avoid becoming a security issue itself

A mature presentation does not only say what the scanner checks.

A mature presentation also says:

- what the scanner itself protects against
- what risks still exist
- what should happen before production use

## The Best Opening Line for This Section

Say:

"The biggest security lesson in this project is that building a scanner introduces its own attack surface. So I looked at security in two directions: the security findings the system detects, and the security risks created by the scanner architecture itself."

That is an excellent framing sentence.

## Part 1: Security Strengths Already Present in the Codebase

These are real controls visible in the repository.

### 0. Shift-Left Security in GitHub Actions

Relevant code:

- `.github/workflows/pr-security.yml`
- `.github/semgrep/agentic-pr.yml`
- `backend/app/sast/cli.py`

What it does:

- scans the base snapshot of a pull request
- scans the PR snapshot
- compares the two sets of findings
- comments on the PR with a markdown summary
- can fail the workflow if blocking findings are added

Why it matters:

- security is moved earlier into code review
- developers get feedback before merge
- the project is not just reactive scanning of deployed targets

What to say:

"A major strength of the project is that it also includes a shift-left security workflow in GitHub Actions. That means security review can happen during pull requests, not only after the application is running."

### 1. Authorization Confirmation Before Scanning

Relevant code:

- `frontend/components/InputSection.tsx`
- `backend/app/routers/scans.py`

What it does:

- the UI presents a warning modal
- the backend rejects requests if `authorization_confirmed` is false

Why it matters:

- web scanning without permission is unethical and often illegal
- putting the reminder in both the UI and backend is better than a frontend-only warning

What to say:

"I included an authorization gate because scanning is not just a technical action; it has legal and ethical implications. The frontend asks for explicit confirmation, and the backend enforces that confirmation rather than trusting the client alone."

### 2. Input Validation on Target URLs

Relevant code:

- `backend/app/schemas.py`

What it does:

- uses `HttpUrl` validation in the Pydantic schema

Why it matters:

- malformed input is rejected early
- validation reduces accidental misuse

Important nuance:

- URL validation is useful, but it is not enough by itself to stop SSRF or dangerous destinations

What to say:

"I validate the submitted target as a proper URL, which is a basic but necessary first step. That said, syntax validation is not the same thing as destination safety, so I would not treat that as complete SSRF protection."

### 3. Bounded Scanning Behavior

Relevant code:

- `backend/app/services/scan_orchestrator.py`
- `backend/app/scanner/a03_injection.py`
- `backend/app/config.py`

Controls visible in code:

- scanner timeout configuration
- 60-second timeout per module
- max 5 redirects in the HTTP client
- first 5 forms only for one XSS form check
- fixed payload lists
- module-level exception isolation

Why it matters:

- scanners can easily become unstable or abusive
- bounded behavior reduces the chance of harming target systems or hanging indefinitely

What to say:

"One of the security-minded design choices was adding operational bounds. I limited request behavior, module duration, payload scope, and form exploration so the scanner stays controlled."

### 4. Failure Isolation Between Modules

Relevant code:

- `backend/app/services/scan_orchestrator.py`

What it does:

- if one module throws an exception or times out, the rest of the scan continues

Why it matters:

- resilience
- a partial failure does not destroy the entire scan

Security value:

- better availability
- less brittle processing of hostile or malformed responses

What to say:

"I treated scanner modules as potentially failure-prone because targets can behave unpredictably. A failure in one module should not take down the entire scan pipeline."

### 5. Restricted CORS Configuration by Default

Relevant code:

- `backend/app/config.py`
- `backend/app/main.py`

What it does:

- `cors_origins` defaults to `http://localhost:4500` and `http://127.0.0.1:4500`

Why it matters:

- it is better than `*`
- it shows awareness of cross-origin exposure

What to say:

"The backend does not expose APIs to every origin by default. The default CORS configuration is limited to the local frontend, which is a safer default for development."

### 6. Chat Restricted to Completed Scans

Relevant code:

- `backend/app/routers/chat.py`

What it does:

- the user cannot chat until the scan is complete

Why it matters:

- the AI receives a stable data snapshot
- avoids partial or inconsistent context

What to say:

"I separated scanning from explanation, and I only allow chat once the scan is complete. That reduces context inconsistency and makes the AI response pipeline easier to reason about."

## Part 2: Security Findings the Product Itself Looks For

This is where you explain what the scanner checks.

Examples visible in the code:

- broken access control
- injection
- security misconfiguration
- vulnerable components
- authentication failures
- integrity failures
- logging and monitoring weaknesses
- SSRF

You do not need to explain all ten OWASP categories in depth.

Instead say:

"The scanner is organized around OWASP Top 10 style modules. For example, it checks for reflected XSS, SQL error indicators, command injection evidence, insecure headers, exposed configuration files, weak cookie flags, technology disclosure, and vulnerable component versions."

## Part 3: Security Risks Still Present in the Current Design

This is where honesty matters most.

If you hide these, the presentation becomes weaker.

If you explain them clearly, the presentation becomes stronger.

### 1. Outbound Request Risk and SSRF Exposure

Relevant code:

- `backend/app/routers/scans.py`
- `backend/app/scanner/http_client.py`

The system makes outbound requests to user-supplied targets.

That is inherently risky.

Current gap:

- there is no visible allowlist, denylist, or private-network restriction
- a malicious user could potentially direct scans toward internal or sensitive destinations if the service were exposed carelessly

What to say:

"The biggest security risk in the current design is outbound request control. Because the scanner fetches user-supplied URLs, production deployment would require SSRF protections such as host allowlisting, private-address blocking, and network-level egress controls."

### 2. TLS Verification Is Disabled

Relevant code:

- `backend/app/routers/scans.py`
- `backend/app/scanner/http_client.py`

The code uses `verify=False`.

Why this was probably done:

- to scan sites with invalid or self-signed certificates

Why it is risky:

- weakens transport authenticity
- could allow man-in-the-middle issues
- acceptable only with explicit scope and strong environment controls

This is one of the most important things to say honestly.

What to say:

"A major tradeoff in the current prototype is that TLS verification is disabled for reachability checks and scanner requests. That improves compatibility with misconfigured targets, but it is not a safe default for production and would need stronger policy controls."

### 3. No Authentication or Multi-Tenant Authorization

Relevant code:

- implied across API routes and frontend flow

Current state:

- the system has scan APIs and history views
- there is no visible login, ownership model, or per-user authorization boundary

Why it matters:

- one user could potentially access another user's scan data in a shared deployment
- scan results may contain sensitive evidence

What to say:

"The current project is strongest as a single-user prototype. A real deployment would need authentication, per-user ownership checks, and stronger access control around stored findings and chat history."

### 4. Sensitive Evidence Storage

Relevant code:

- `backend/app/models.py`
- findings are stored with `evidence`, `description`, `remediation`, and target URLs

Why it matters:

- evidence may contain sensitive HTML, headers, tokens, path details, or internal technology information
- that makes the findings database itself sensitive

What to say:

"The system stores finding evidence so results are actionable, but that also means the persistence layer can contain sensitive target data. For production, I would add retention policies, encryption at rest, redaction rules, and stronger access controls."

### 5. No Visible Rate Limiting or Quotas

Why it matters:

- a scanner can be abused for excessive outbound traffic
- repeated scan creation could stress the service

What to say:

"I do not see rate limiting or scan quotas in the current version, so that would be a required hardening step before exposing the service to multiple users."

### 5.5. CI Security Coverage Is Strong, but Supply Chain Trust Still Matters

Why this matters:

- the GitHub Actions workflow installs external security tools
- CI pipelines are part of the system's trust boundary too

Examples in the workflow:

- Semgrep
- gitleaks
- pip-audit
- npm audit

What to say:

"The GitHub Actions pipeline strengthens the project, but CI itself becomes part of the security surface. In a more mature setup, I would further harden tool pinning, artifact integrity, and secret handling inside the workflow environment."

### 6. LLM Data Exposure and Prompt Safety

Relevant code:

- `backend/app/services/chat_service.py`

Current behavior:

- findings data is packaged into a prompt and sent to Anthropic

Why it matters:

- scan findings can contain sensitive information
- external model providers create a data-governance boundary
- prompt injection and misleading content from findings are concerns

Important nuance:

- the AI is used for explanation, not authoritative scanning
- that is good, but it is still a security and privacy boundary

What to say:

"The chat assistant improves usability, but it creates a third-party data-sharing boundary because scan findings are sent to an external LLM provider. In a stricter environment, I would add redaction, policy filters, explicit data classification, and possibly an internal model option."

### 7. Scanner Safety vs. Scanner Coverage

Why it matters:

- aggressive scanners can be dangerous
- weak scanners can miss issues

The current project appears to favor safer heuristics over aggressive exploitation.

That is a reasonable prototype decision.

What to say:

"I intentionally kept the scanner mostly heuristic and evidence-based rather than highly exploitative. That reduces the risk of harming targets, but it also means some findings are indicators rather than full exploit confirmation."

## Part 4: How to Speak About False Positives and Confidence

This matters a lot in product security.

Good line:

"I tried to preserve nuance by storing confidence levels and by distinguishing between stronger confirmations and weaker indicators. In security tooling, being honest about confidence is part of the product's trust model."

That line sounds excellent.

## Part 5: What You Would Improve Next

This is the exact roadmap you should present if asked how you would harden the system.

### Priority 1: Safe Deployment Boundaries

- add authentication and authorization
- add host allowlists and block private IP ranges
- run scans in isolated workers or containers
- enforce outbound network policy

### Priority 2: Data Protection

- encrypt sensitive records
- redact evidence where possible
- add retention and deletion policies
- control who can access findings and chat history

### Priority 3: Abuse Resistance

- add rate limiting
- add per-user scan quotas
- add concurrency limits
- add audit logging

### Priority 4: LLM Hardening

- classify and redact findings before prompt construction
- add prompt safety guards
- add model-provider isolation options
- log AI usage carefully without leaking sensitive data

## Best Closing Line for This Section

Say:

"If I were summarizing the security posture honestly, I would say the project already demonstrates security awareness in its workflow, scan boundaries, and modular detection logic, but it still needs platform hardening before it should be treated as a production-grade scanning service."

## If You Get the Question: "Would You Ship This?"

Strong answer:

"I would ship it as a controlled prototype or internal demo, not as a public production scanner yet. The main blockers are authentication, outbound request restrictions, secure evidence handling, and stronger deployment isolation."

That answer is balanced, mature, and trustworthy.
