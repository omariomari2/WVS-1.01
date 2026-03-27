# 15-Minute Presentation Plan for a Product Security Manager

## Purpose of This Folder

This folder is a speaker-ready presentation pack for explaining the project to a product security manager.

The goal is not just to say what the project does.

The real goal is to show four things clearly:

1. You can think algorithmically.
2. You understand your architecture and why you made your design choices.
3. You take security seriously and can talk about both strengths and weaknesses honestly.
4. You can reflect on engineering challenges instead of pretending the project was easy.

This pack assumes the presenter is a sophomore. That means the language is intentionally supportive, explicit, and structured so you can present with confidence even if this is one of your first technical demos to a security leader.

## What the Project Is

This project is a web security scanning platform with a frontend, a FastAPI backend, OWASP-focused scanning modules, persistent storage for findings, real-time scan progress updates, and an AI chat assistant that helps explain findings in plain English.

Frontend:

- Next.js app in `frontend/`
- Starts scans, shows scan history, displays findings, and provides a chat interface

Backend:

- FastAPI app in `backend/app/`
- Accepts scan requests, runs scanner modules, stores findings, streams progress, and serves AI chat responses

Scanner model:

- Modular scanner classes for OWASP Top 10 categories
- Each module focuses on a different kind of weakness

## Very Important Audience Reminder

A product security manager usually cares about:

1. Whether the system is safe to operate
2. Whether the architecture is maintainable
3. Whether the findings are actionable
4. Whether the team understands risks, tradeoffs, and next steps

So when you present, do not focus only on features.

Focus on:

- risk
- boundaries
- tradeoffs
- technical reasoning
- honesty about limitations

## Recommended 15-Minute Timing

Use this exact pacing if you want a strong, realistic flow.

### Minute 0 to 2: Opening and Project Overview

Say:

"Today I'm presenting `wvs`, a security scanning platform for web applications. The system lets a user submit a target URL, runs OWASP-oriented checks in the backend, stores findings, streams progress back to the frontend, and then uses AI to explain the results in plain English. I want to focus on four areas: algorithmic thinking, architecture and technical decisions, security considerations, and the challenges I encountered while building it."

Your goal in the first two minutes:

- establish what the system does
- show confidence
- tell the manager exactly how you will structure the discussion

### Minute 2 to 5: Algorithmic Thinking

Use `01_algorithmic_thinking_dsa.md`.

Main point:

- this is not "just CRUD"
- the project uses data structures and control flow decisions intentionally

### Minute 5 to 8: Architecture and Technical Decisions

Use `02_architecture_and_technical_decisions.md`.

Main point:

- the system is modular on purpose
- the architecture reflects maintainability, responsiveness, and separation of concerns

### Minute 8 to 10: GitHub Actions and DevSecOps Workflow

Use `06_github_actions_and_workflow.md`.

Main point:

- the project is not only an interactive scanner
- it also shifts security left into pull request review with automated scanning and gating

### Minute 10 to 13: Security Considerations

Use `03_security_considerations.md`.

This is the most important section.

Main point:

- because the product is itself a security tool, the system has to be treated as both a defender and a potential source of risk

### Minute 13 to 14: Development Challenges

Use `04_development_challenges.md`.

Main point:

- strong engineers explain what was difficult, what tradeoffs were made, and what still needs improvement

### Minute 14 to 15: Close

Say:

"The main thing I want to leave you with is that this project was not only about building a scanner. It was about building a system that organizes security checks, communicates risk clearly, and makes deliberate tradeoffs around safety, usability, and extensibility. If I continued this project, my next steps would focus on hardening the scanner itself, especially around authentication, outbound request control, and secure deployment boundaries."

## One-Sentence Summary You Can Memorize

"`wvs` is a modular web application security scanner with real-time progress tracking and AI-assisted remediation guidance."

## Two-Sentence Summary You Can Memorize

"This project accepts an authorized target URL, runs modular OWASP-focused security checks in the backend, stores findings, and presents them in a frontend dashboard. It also includes an AI assistant that explains findings in plain English so the tool is useful not just for detection, but also for communication and remediation."

## If You Get Nervous

Use this fallback structure for every answer:

1. What the system does
2. Why it was designed that way
3. What security tradeoff exists
4. What you would improve next

Example:

"The scanner runs modules in a controlled sequence. I chose that because it keeps progress reporting simple and reduces coordination complexity. The tradeoff is that scans can take longer than a fully parallel design. If I continued, I would likely add bounded concurrency so I could improve speed without losing control."

## What Not to Do

Do not:

- claim the scanner is production-ready without qualification
- say "it is secure" as a blanket statement
- hide limitations like `verify=False`, lack of authentication, or missing rate limits
- oversell AI as if it replaces security expertise

Do:

- explain current safeguards
- explain current gaps
- explain what hardening would come next

## Suggested File Order for Practice

Practice the files in this order:

1. `00_presentation_plan.md`
2. `02_architecture_and_technical_decisions.md`
3. `03_security_considerations.md`
4. `01_algorithmic_thinking_dsa.md`
5. `06_github_actions_and_workflow.md`
6. `04_development_challenges.md`
7. `05_qna_prep.md`

That order helps you internalize the story first, then the evidence, then the backup answers.
