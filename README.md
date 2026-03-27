# WVS

WVS is an AI endpoint security platform for software delivery.

The core idea behind the project is simple: AI agents now behave like super-privileged insiders. They can read large amounts of code quickly, generate changes at scale, and move information across development systems with very little friction. WVS is designed to put visibility, policy, evidence, and human oversight around that workflow.

In the current repository, WVS is centered on pull-request security. It scans changed sandbox projects in CI, normalizes and classifies findings, comments on the PR with both human-readable and machine-readable evidence, imports those findings into the app, and lets a reviewer inspect, explain, export, and respond to them from the frontend.

## What WVS Does

Today, the strongest end-to-end flow in this repo is:

1. A pull request touches code under `sandbox/**`.
2. GitHub Actions runs the PR security workflow.
3. The changed scope is scanned with Semgrep, Gitleaks, and dependency-audit tooling where relevant.
4. Findings are normalized into a common schema and classified by severity and blocking policy.
5. A PR summary is posted back to GitHub, along with an embedded machine-readable findings payload.
6. WVS imports the PR, stores the findings and commit context, and exposes them in the app.
7. A reviewer can inspect findings, ask the AI for grounded explanation, export evidence, or trigger bounded remediation actions.

This makes WVS more than a scanner UI. It is a control plane around AI-assisted code review and remediation workflows.

## Why This Is AI Endpoint Security

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

## Current Architecture

The current codebase is organized around a few main layers:

- GitHub Actions sensor layer
  CI detects changed scope, runs scanners, normalizes findings, and applies blocking policy.

- Backend control plane
  FastAPI handles PR ingest, findings APIs, chat, export, and rectify actions.

- Durable security memory
  Scans, findings, PR commits, and chat history are stored so reviews are grounded in persistent evidence.

- Analyst console
  The Next.js frontend lets a reviewer inspect findings, ask for explanation, export reports, and choose follow-up actions.

- Controlled response layer
  WVS supports bounded remediation paths such as PR comments and local prompt-based code-fix workflows.

## Repo Highlights

- `.github/workflows/pr-security.yml`
  Pull-request security workflow for changed sandbox projects.

- `backend/app/sast/`
  Snapshot scanning, normalization, diffing, and reporting logic for PR findings.

- `backend/app/services/pr_ingest.py`
  Imports PR metadata and findings into WVS.

- `backend/app/services/chat_service.py`
  Builds grounded AI explanation context from stored findings.

- `backend/app/services/rectify_service.py`
  Handles bounded follow-up actions for findings.

- `frontend/`
  Analyst-facing app for reviewing imported findings and interacting with the workflow.

## Current Scope

This repository currently emphasizes internal PR security automation and review workflows. The current implementation is strongest as an internal prototype and control-plane foundation rather than a fully hardened production platform.

That is intentional. The architecture already exposes the important seams:

- telemetry collection
- evidence normalization
- policy evaluation
- persistence
- analyst review
- AI-assisted explanation
- bounded remediation

Those are the foundations needed for a mature AI endpoint security product.

## Docs

The `details/` folder contains the product-security write-up for this architecture, including:

- presentation framing
- architecture and technical decisions
- security considerations
- development challenges
- Q&A prep
- GitHub workflow explanation
- a pipeline roadmap with tools, algorithms, technologies, and principles

If you want the quickest visual overview, start with `details/tools.md`.
