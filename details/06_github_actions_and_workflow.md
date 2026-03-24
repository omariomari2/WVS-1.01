# GitHub Actions, Workflow Design, and DevSecOps Story

## Why This File Exists

This project is not only a web application with a frontend and backend.

It also includes an automated pull request security workflow.

That matters a lot to a product security manager because it shows the project thinks about security in two modes:

1. runtime scanning of a target application
2. pre-merge scanning of source code and dependencies in the development workflow

If you leave this out, the presentation misses an important part of the engineering story.

## The Main Message You Should Say

"An important part of the project is that security is not only something the product does after deployment. The repository also contains a GitHub Actions workflow that scans pull requests, compares new findings against the base branch, posts a report back into the PR, and can block merges when serious issues are introduced."

That is a strong sentence. Memorize it.

## Relevant Files

- `.github/workflows/pr-security.yml`
- `.github/semgrep/agentic-pr.yml`
- `backend/app/sast/cli.py`
- `backend/app/sast/normalize.py`
- `backend/app/sast/diff_engine.py`
- `backend/app/sast/reporter.py`

## What the Workflow Does

The workflow is triggered on:

- `pull_request`

The workflow has three main jobs:

1. `scan-base`
2. `scan-pr`
3. `compare-and-report`

This structure is important because it shows the workflow is not just running a scanner once.

It is comparing change over time.

That is much more useful than a raw one-time result dump.

## Job 1: `scan-base`

What it does:

- checks out the base branch snapshot of the pull request
- installs Python and Node
- installs security tools
- runs the project's SAST CLI to scan that snapshot
- uploads the findings as an artifact

Why that matters:

- it creates a baseline
- a baseline lets you tell the difference between old problems and newly introduced problems

What to say:

"The workflow first scans the base version of the code so the system has something meaningful to compare against. That helps avoid punishing developers for pre-existing issues when the real question is what changed in this pull request."

## Job 2: `scan-pr`

What it does:

- checks out the PR merge snapshot
- installs the same tooling
- runs the same scan process
- uploads findings for the proposed change

Why that matters:

- both snapshots are scanned consistently
- the comparison is fair because it uses the same tools and normalization path

What to say:

"The PR snapshot is scanned using the same process as the base snapshot, which keeps the comparison consistent and reduces noise from environmental differences."

## Job 3: `compare-and-report`

What it does:

- downloads both artifacts
- compares base findings with PR findings
- builds a markdown report
- emits GitHub annotations
- uploads report artifacts
- comments on the pull request
- fails the job if blocking findings are introduced

Why this is strong:

- the workflow turns scan output into developer-facing feedback
- it is integrated into code review, not hidden in a separate system
- blocking logic means security can influence merge decisions

What to say:

"The most important job is the comparison step. Instead of flooding the team with a list of everything wrong, it highlights what is new, what was resolved, and what stayed the same. That makes the security feedback far more actionable."

## Security Tools Used in the Workflow

### 1. Semgrep

Configured in:

- `.github/semgrep/agentic-pr.yml`

Why it matters:

- custom rules are defined for risks relevant to the project
- examples include hardcoded secrets, SQL injection, weak auth, insecure defaults, raw HTML rendering, SSRF patterns, and command injection

What to say:

"Semgrep gives the workflow custom static analysis rules, which means the project is not relying only on generic defaults. It defines project-relevant checks in a way that is visible and maintainable."

### 2. Gitleaks

Why it matters:

- looks for secrets committed to the repo
- helps catch accidental leakage early

What to say:

"Gitleaks is a good complement because code quality scanners do not always catch exposed secrets well. Secret detection deserves its own tool."

### 3. pip-audit

Why it matters:

- scans Python dependencies for known vulnerabilities
- covers the backend dependency chain

### 4. npm audit

Why it matters:

- scans Node dependencies
- covers the frontend dependency chain

Important insight:

- this means the workflow covers both first-party code patterns and third-party dependency risk

That is a very good point to make.

## Why the Normalization Layer Matters

Relevant code:

- `backend/app/sast/normalize.py`

Different tools produce different output formats.

That creates a problem:

- how do you compare findings from multiple tools in one consistent way?

The solution in this project:

- normalize tool-specific output into a shared `ScanFinding` structure

This is an excellent architectural idea.

Why:

- one reporting format
- one diffing format
- one blocking policy model

What to say:

"A key technical decision was adding a normalization layer. Semgrep, gitleaks, pip-audit, and npm audit all speak different output formats, so I normalized them into one common finding model before comparing or reporting anything."

## Why the Diff Engine Matters

Relevant code:

- `backend/app/sast/diff_engine.py`
- `backend/app/sast/base.py`

This is one of the smartest parts of the workflow.

The workflow does not just ask:

"Are there findings?"

It asks:

- which findings are new
- which findings were resolved
- which findings are unchanged
- which new findings are severe enough to block the PR

That is a much more mature question.

The engine uses fingerprints so findings can still match even if line numbers move.

That is especially important in real repositories where code shifts often.

What to say:

"The diff engine focuses the workflow on change, not just existence. That is important because developers can act on newly introduced risk more effectively than on a huge undifferentiated backlog."

## Why a Product Security Manager Will Care

A product security manager will usually like this workflow for five reasons:

1. it pushes security earlier into development
2. it reduces review noise by comparing snapshots
3. it covers both code patterns and dependency issues
4. it creates an audit trail through artifacts and PR comments
5. it introduces policy through blocking thresholds

This is not just CI.

It is part of the product's security operating model.

## Security Strengths of the Workflow

- pull-request trigger encourages early feedback
- concurrency control prevents duplicated overlapping runs
- artifacts preserve evidence
- PR comments make results visible in the developer workflow
- fail threshold creates enforceable policy

What to say:

"From a security operations perspective, the workflow is valuable because it turns scans into traceable, reviewable, and enforceable development feedback."

## Limitations and Honest Tradeoffs

Be candid here too.

### 1. Tooling Trust and Supply Chain

The workflow downloads and installs security tools in CI.

That means:

- the toolchain itself becomes part of the trust boundary
- version pinning and integrity verification matter

### 2. Static Analysis Noise

Semgrep-style checks can produce false positives.

That is why normalization, severity, confidence, and diffing matter so much.

### 3. Snapshot Scanning Is Not Runtime Scanning

This workflow is strong, but it does not replace active runtime testing.

That is important to say.

A great line:

"The GitHub workflow complements the runtime scanner. It does not replace it. One catches issues in code before merge, and the other checks live behavior against a running target."

### 4. Policy Thresholds Need Organizational Tuning

The workflow currently uses:

- `--fail-threshold high`

That is sensible, but in a larger organization this would likely be tuned over time.

## Best 90-Second Version of This Section

Say:

"The repo also includes a GitHub Actions PR security workflow, and that is an important part of the overall design. On every pull request, it scans both the base branch snapshot and the proposed PR snapshot using gitleaks, Semgrep, pip-audit, and npm audit. Then it normalizes the findings into a common schema, compares them with a diff engine, generates markdown and JSON reports, comments on the PR, and can fail the workflow if new high-severity findings are introduced. I think this is important because it shifts security left, reduces noise by focusing on new risk, and ties security feedback directly into the developer workflow."

## If Someone Asks, "Why Is This Important to the Presentation?"

Use this answer:

"Because the workflow shows that the project is not only a scanner UI. It also demonstrates how security analysis can be operationalized in the software delivery pipeline."
