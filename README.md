### WVS

WVS is an AI endpoint security platform for software delivery, modeled after PANW security reports and inspired by the acquisition move of KOI.

AI agents now behave like super-privileged insiders. They can read large amounts of code quickly, generate changes at scale, and move information across development systems with very little friction. WVS is designed to put visibility, policy, evidence, and human oversight around that workflow.

In summary:
1. A pull request touches code under `sandbox/**`.
2. GitHub Actions runs the PR security workflow.
3. The changed scope is scanned with Semgrep, Gitleaks, and dependency-audit tooling where relevant.
4. Findings are normalized into a common schema and classified by severity and blocking policy.
5. A PR summary is posted back to GitHub, along with an embedded machine-readable findings payload.
6. WVS imports the PR, stores the findings and commit context, and exposes them in the app.
7. A reviewer can inspect findings, ask the AI for grounded explanation, export evidence, or trigger bounded remediation actions.

Traditional endpoint security focused on user devices, binaries, and process execution. WVS applies that same security mindset to software delivery endpoints:
- pull requests
- CI runners
- repositories
- findings stores
- AI explanation surfaces
- AI-assisted remediation paths

Instead of assuming AI is safe because it is helpful, WVS assumes agentic workflows need the same discipline as any privileged actor:
- least privilege
- evidence before action
- human-in-the-loop review
- bounded context
- auditability

