# Q&A Preparation for a Product Security Manager

## How to Use This File

This file is your backup material.

Do not try to memorize every line exactly.

Instead:

1. read the question
2. understand the point behind the question
3. practice the short answer
4. use the longer version only if needed

## Question 1: "What problem does this project solve?"

Short answer:

"It helps users scan a web application for OWASP-style security issues, review the results in a structured dashboard, and understand the findings through AI-assisted explanations."

Longer answer:

"The project is meant to reduce the gap between raw security detection and user understanding. It runs modular scans, stores evidence, summarizes risk, and then helps a user interpret and prioritize the results."

## Question 2: "What is technically interesting about it?"

Short answer:

"The most interesting part is the combination of modular active scanning, real-time progress updates, structured persistence of findings, and an explanation layer that uses the stored scan context rather than guessing blindly."

## Question 3: "Where is the algorithmic thinking?"

Short answer:

"In the scan pipeline, bounded search design, dictionary and set-based lookup, severity aggregation, deduplication, and fingerprint-based diffing of findings."

## Question 4: "Why did you choose this architecture?"

Short answer:

"I wanted clear separation of concerns. The frontend handles workflow, the API layer handles requests, the orchestrator handles scan coordination, scanner modules handle detection, and the chat service handles explanation."

## Question 5: "What is your strongest design decision?"

Short answer:

"The modular scanner abstraction. It keeps the system extensible and prevents the scanning logic from collapsing into one large file."

Longer answer:

"The base scanner and per-category module design made it possible to add checks in a structured way while reusing common behavior like request helpers and finding creation. That choice supports maintainability, testing, and future expansion."

## Question 6: "What are the biggest security risks in your current implementation?"

Short answer:

"The biggest ones are outbound request control, disabled TLS verification, lack of authentication, and sensitive evidence handling."

This is a very important answer. Be confident and direct.

## Question 7: "Would you deploy this to production?"

Short answer:

"Not publicly in its current form. I would treat it as a prototype or internal demo until authentication, network isolation, rate limiting, and secure data handling are added."

## Question 8: "Why is TLS verification disabled?"

Short answer:

"It was likely a compatibility choice for scanning misconfigured targets, but I would not keep that as a default in a production deployment."

Better version:

"Disabling verification makes the scanner more tolerant of broken certificates, which can be useful in testing. But it weakens trust in transport integrity, so for a hardened deployment I would move to stricter policy-based handling instead."

## Question 9: "How do you avoid false positives?"

Short answer:

"I do not claim perfect avoidance, but the project tries to preserve nuance through confidence levels, evidence capture, bounded heuristics, and a distinction between indicators and stronger confirmations."

## Question 10: "What would you improve first?"

Short answer:

"Authentication, outbound request restrictions, worker isolation, and secure evidence handling."

## Question 11: "Why include AI at all?"

Short answer:

"Because understanding findings is often harder than generating them. I used AI as an explanation layer, not as the source of truth for vulnerability detection."

## Question 12: "What would concern you most as a security reviewer?"

Short answer:

"The scanner's outbound network behavior and the sensitivity of stored evidence."

Longer answer:

"Because the system fetches user-supplied targets, I would want strong SSRF controls, network sandboxing, and explicit egress policy. I would also want a clear policy for encrypting, redacting, and retaining scan evidence."

## Question 13: "How does the project support maintainability?"

Short answer:

"It separates routes, services, models, scanner modules, and frontend components, so each part has a clear role."

## Question 14: "Why not let the AI do the scanning too?"

Short answer:

"Because scanning should stay grounded in deterministic program logic and evidence collection. AI is useful for explanation, but I would not want it to be the primary vulnerability detector."

## Question 15: "How would you scale this?"

Short answer:

"I would move scanning into isolated worker processes or containers, introduce a queue, replace SQLite with a production database, and enforce stronger tenancy and rate controls."

## Question 16: "What did you learn from this project?"

Short answer:

"I learned that security tools need both technical detection logic and careful product engineering around trust, communication, and operational safety."

## Question 17: "What is one thing you are proud of?"

Short answer:

"I am proud that the project is not just a scanner. It tries to make findings understandable through structure, evidence, summaries, and post-scan explanation."

## Question 18: "What is one thing you would criticize about your own project?"

Short answer:

"I would criticize the lack of hardening around deployment boundaries, especially authentication and outbound network safety."

This is a great answer because it shows honesty.

## Question 19: "How would you describe the maturity level of the project?"

Short answer:

"I would describe it as a thoughtful prototype with strong modularity and a clear hardening roadmap, rather than a finished production-grade security platform."

## Question 20: "What should I remember after this presentation?"

Short answer:

"That I approached the project as a security-sensitive system, not just a coding exercise. The architecture, algorithmic choices, and the honest discussion of risks are the main things I want you to remember."

## Closing Advice

If you do not know an answer, do not panic.

Use this sentence:

"My current understanding is this: ..."

Then say:

1. what the system currently does
2. what the tradeoff is
3. what you would improve next

That structure will carry you through most questions.
