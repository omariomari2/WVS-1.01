# Development Challenges and What They Taught Me

## Important Note for This Section

This repository does not contain a full personal engineering diary.

So the challenge discussion below is reconstructed from the architecture, code structure, and tradeoffs visible in the project.

That is okay.

In fact, that is often how engineers talk about development: they infer the hard parts from the actual design decisions and explain what had to be balanced.

When you present this section, you can say:

"These are the main engineering challenges reflected in the code and architecture decisions."

That wording is honest and strong.

## Challenge 1: Balancing Coverage With Safe Behavior

Why this was difficult:

- a security scanner should find meaningful issues
- but a scanner can also become noisy, slow, or even harmful

Evidence in the code:

- per-module timeouts in `backend/app/services/scan_orchestrator.py`
- fixed payload lists in `backend/app/scanner/a03_injection.py`
- limited form scanning
- sequential module orchestration

What this challenge really means:

- every extra payload increases coverage
- but every extra payload also increases scan time, load on the target, and the chance of false positives

How to explain it:

"One major challenge was deciding how aggressive the scanner should be. I wanted enough coverage to catch meaningful problems, but I also needed to keep the scanner bounded and responsible. That led to choices like timeouts, limited payload sets, and early exits after strong evidence."

Lesson:

- security engineering is often about calibrated restraint, not maximum aggression

## Challenge 2: Building a System That Feels Real-Time

Why this was difficult:

- scans are long-running
- HTTP request-response by itself is not enough for a good user experience

Evidence in the code:

- WebSocket progress manager in `backend/app/websocket/scan_progress.py`
- frontend scan status UI in `frontend/components/HomePage.tsx`
- polling fallback if WebSockets fail

Why this was a real engineering challenge:

- the backend has to manage long-lived execution
- the frontend has to show progress cleanly
- failure modes have to be handled without leaving the user confused

How to explain it:

"A normal CRUD app can get away with simple request-response flow, but a scanner cannot. I had to build a real-time feedback loop so the user knows the system is still working. That introduced complexity in both the backend and frontend, especially around progress broadcasting and fallback behavior."

Lesson:

- product quality includes operational visibility, not just core functionality

## Challenge 3: Keeping the Architecture Extensible

Why this was difficult:

- adding one scanner is easy
- adding ten scanners without creating a mess is harder

Evidence in the code:

- `BaseScannerModule` in `backend/app/scanner/base.py`
- one scanner file per OWASP area
- orchestration separated from module logic

What had to be solved:

- shared logic should not be duplicated
- specialized logic should remain independent
- adding new checks should not require redesigning the system

How to explain it:

"I needed the codebase to scale structurally, not just functionally. That is why I introduced a base scanner abstraction and kept each OWASP category in its own module. The challenge was designing enough shared structure to avoid duplication without making every scanner feel constrained."

Lesson:

- extensibility is easier when planned early than retrofitted later

## Challenge 4: Avoiding False Positives While Still Producing Actionable Findings

Why this was difficult:

- security tools lose trust quickly if they over-report
- under-reporting is also a problem

Evidence in the code:

- confidence values in findings
- differentiated severities
- early returns after stronger confirmations
- evidence fields attached to findings

What this challenge means:

- a finding is not just "true" or "false"
- findings often exist on a confidence spectrum

How to explain it:

"Another challenge was credibility. A security tool has to explain why it believes something is wrong. That is why the finding model includes severity, confidence, evidence, and remediation. I wanted the system to do more than say 'something might be bad'; I wanted it to show reasoning."

Lesson:

- trustworthy security products communicate uncertainty clearly

## Challenge 5: Integrating AI Without Letting AI Become the Whole Product

Why this was difficult:

- AI can improve usability
- AI can also blur boundaries if it is mixed directly into core detection

Evidence in the code:

- chat only becomes available after scan completion
- findings are stored first, then used as chat context
- chat service is separate from scanning service

Why this matters:

- the scanner should remain deterministic where possible
- AI should explain results, not replace detection logic

How to explain it:

"A challenge was deciding where AI belongs. I did not want the model deciding whether a vulnerability existed. Instead, I used the AI after the scan to translate technical findings into plain English remediation guidance. That keeps the scanner grounded in program logic while still improving usability."

Lesson:

- AI is most useful here as an explanation layer, not an authority layer

## Challenge 6: Security Tooling Creates Security Risk

Why this was difficult:

- the product makes outbound requests to user-supplied URLs
- that immediately creates SSRF, abuse, and data-handling concerns

Evidence in the code:

- authorization confirmation flow
- outbound HTTP client
- current lack of stronger destination controls

Why this is an honest challenge to discuss:

- it shows maturity
- it shows you understand that security tools are high-risk systems

How to explain it:

"A particularly important challenge was realizing that the scanner itself creates risk. The moment a backend starts making requests to user-supplied targets, you have to think about SSRF, transport safety, rate limits, and what data might be stored. So part of the development challenge was not just building the scanner, but understanding the scanner as a security-sensitive application."

Lesson:

- defensive tools still need defensive architecture

## Challenge 7: Turning Raw Findings Into a Product Experience

Why this was difficult:

- raw vulnerabilities are not enough
- users need summaries, prioritization, scan history, and explanations

Evidence in the code:

- findings summary in `backend/app/routers/findings.py`
- dashboard and chart components in the frontend
- chat explanation workflow

How to explain it:

"The challenge was not only discovering security issues, but presenting them in a way a user can act on. That is why the system groups findings by severity, keeps scan history, and adds AI-based explanation. The engineering challenge was bridging detection with communication."

Lesson:

- useful security tooling is both analytical and communicative

## Challenge 8: Designing for Maintainability as a Student Project

Why this was difficult:

- student projects often grow fast and become tangled
- it is easy to hard-code logic directly into routes or components

Evidence in the code:

- routers separated from services
- services separated from scanner modules
- frontend components divided by responsibility

How to explain it:

"I tried not to let the project collapse into a monolith. Even as a student project, I wanted the code to reflect maintainable engineering practices, so I separated routes, services, models, scanner modules, and frontend components by role."

Lesson:

- maintainability is not only for large companies; it matters even in prototypes

## Challenge 9: Turning Security Logic Into a CI Workflow

Why this was difficult:

- raw scanner logic is not enough for team adoption
- the results have to fit into the pull request workflow developers already use

Evidence in the code:

- `.github/workflows/pr-security.yml`
- `backend/app/sast/cli.py`
- `backend/app/sast/normalize.py`
- `backend/app/sast/diff_engine.py`

What had to be solved:

- run multiple tools consistently
- compare base and head snapshots
- normalize different output formats
- decide which findings should actually block a PR

How to explain it:

"Another challenge was moving from a standalone scanner mindset to a workflow mindset. It was not enough to detect issues; the project also needed a way to present security feedback during pull requests. That required snapshot scanning, normalization, comparison, reporting, and merge-gating logic."

Lesson:

- security value increases when detection is embedded into the development process

## Best 2-Minute Version of This Section

Say:

"The biggest development challenges were balancing scan coverage with safe behavior, making the system feel real-time, keeping the architecture extensible, and being honest about the risks introduced by the scanner itself. I also had to think carefully about false positives and where AI should sit in the product. Overall, the project taught me that security tools are not just about detection logic; they are about building a trustworthy system around that logic."

## If the Manager Asks, "What Was the Hardest Part?"

Best answer:

"The hardest part was balancing practicality, safety, and usefulness at the same time. It is easy to build a more aggressive scanner or a more polished UI in isolation, but building a system that scans responsibly, explains results clearly, and stays modular was the real challenge."

## If the Manager Asks, "What Would You Do Differently?"

Best answer:

"I would invest earlier in hardening for production-style deployment, especially around authentication, outbound request controls, and worker isolation. The current structure gives me a good base for that, but those controls would be my next major step."
