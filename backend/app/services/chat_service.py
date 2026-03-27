import json
from collections.abc import AsyncGenerator

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import ChatMessage, Finding, Scan


SYSTEM_PROMPT_URL = """You are VenomAI, a cybersecurity expert assistant. You help users understand web security scan results in plain English.

A security scan was performed against: {target_url}

Here is a summary of the scan findings:
{findings_json}

When the user asks about a finding or security topic:
1. Explain what the vulnerability is in plain, non-technical English.
2. Explain why it matters and what real-world impact it could have.
3. Describe how an attacker might exploit it (without exploit code).
4. Give specific, actionable remediation steps.
5. Provide short code examples when helpful.

Response format requirements:
- Use markdown with these exact section headers:
## What It Means
## Why It Matters
## How To Fix It
## What To Check Next
- Use complete sentences only (no fragments).
- Add blank lines between sections and list items.
- If confidence is low, include one line that starts with: Confidence:
- Do not use emojis.

Be precise, actionable, and encouraging. Security can feel overwhelming, so help the user prioritize and move forward clearly."""

SYSTEM_PROMPT_PR = """You are VenomAI, a cybersecurity expert assistant specializing in PR security reviews. You help developers understand security findings in pull requests and write secure code.

PR: {pr_title} (#{pr_number})
Repository: {repo_owner}/{repo_name}
Branch: {pr_branch} -> {base_branch}
URL: {pr_url}

Here are the security findings from the SAST scan of this PR:
{findings_json}

When the user asks about a finding:
1. Explain the vulnerability in the context of the specific file and code.
2. Explain the real-world attack scenario.
3. Provide a concrete code fix with before/after snippets.
4. Reference OWASP and CWE when relevant.
5. Suggest how to validate the fix.

Response format requirements:
- Use markdown with these exact section headers:
## What It Means In This PR
## Why It Matters
## How To Fix It
## Validation Steps
- Use complete sentences only (no fragments).
- Add blank lines between sections and list items.
- Include file paths and line references when available.
- If confidence is low, include one line that starts with: Confidence:
- Do not use emojis.

Be concise, concrete, and practical for the developer who must patch the code quickly."""


async def build_chat_context(db: AsyncSession, scan_id: str) -> tuple[str, list[dict]]:
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise ValueError("Scan not found")

    result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )
    findings = result.scalars().all()

    findings_data = []
    for f in findings:
        entry: dict = {
            "id": f.id,
            "category": f"{f.owasp_category}: {f.owasp_name}",
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "remediation": f.remediation,
            "confidence": f.confidence,
        }
        if f.file_path:
            entry["file_path"] = f.file_path
        if f.line_number:
            entry["line_number"] = f.line_number
        if f.code_snippet:
            entry["code_snippet"] = f.code_snippet
        if f.diff_hunk:
            entry["diff_hunk"] = f.diff_hunk[:500]
        if f.cwe:
            entry["cwe"] = f.cwe
        if f.rule_id:
            entry["rule_id"] = f.rule_id
        findings_data.append(entry)

    if scan.scan_type == "pr":
        system_prompt = SYSTEM_PROMPT_PR.format(
            pr_title=scan.pr_title or "Untitled",
            pr_number=scan.pr_number or "?",
            repo_owner=scan.repo_owner or "?",
            repo_name=scan.repo_name or "?",
            pr_branch=scan.pr_branch or "?",
            base_branch=scan.base_branch or "?",
            pr_url=scan.pr_url or scan.target_url,
            findings_json=json.dumps(findings_data, indent=2),
        )
    else:
        system_prompt = SYSTEM_PROMPT_URL.format(
            target_url=scan.target_url,
            findings_json=json.dumps(findings_data, indent=2),
        )

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.scan_id == scan_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    history = [{"role": m.role, "content": m.content} for m in messages]

    return system_prompt, history


async def stream_chat_response(
    db: AsyncSession,
    scan_id: str,
    user_message: str,
) -> AsyncGenerator[str, None]:
    """Stream a Claude response for the given message in the context of a scan."""
    system_prompt, history = await build_chat_context(db, scan_id)

    # Save user message
    user_msg = ChatMessage(scan_id=scan_id, role="user", content=user_message)
    db.add(user_msg)
    await db.commit()

    # Build messages for Claude
    messages = history + [{"role": "user", "content": user_message}]

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    full_response = ""
    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            full_response += text
            yield text

    # Save assistant message
    assistant_msg = ChatMessage(scan_id=scan_id, role="assistant", content=full_response)
    db.add(assistant_msg)
    await db.commit()

