import json
from collections.abc import AsyncGenerator

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import ChatMessage, Finding, Scan


SYSTEM_PROMPT_TEMPLATE = """You are VenomAI, a cybersecurity expert assistant. You help users understand web security scan results in plain English.

A security scan was performed against: {target_url}

Here is a summary of the scan findings:
{findings_json}

When the user asks about a finding or security topic:
1. Explain what the vulnerability is in plain, non-technical English
2. Explain why it matters and what real-world impact it could have
3. Describe how an attacker might exploit it (without providing actual exploit code)
4. Give specific, actionable steps to fix the issue
5. Provide code examples for remediation where helpful

Be precise, actionable, and encouraging. Security can feel overwhelming - help the user understand what to prioritize and that these issues are fixable."""


async def build_chat_context(db: AsyncSession, scan_id: str) -> tuple[str, list[dict]]:
    """Build system prompt with findings context and load chat history."""
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise ValueError("Scan not found")

    # Load findings
    result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )
    findings = result.scalars().all()

    findings_data = []
    for f in findings:
        findings_data.append({
            "id": f.id,
            "category": f"{f.owasp_category}: {f.owasp_name}",
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "remediation": f.remediation,
            "confidence": f.confidence,
        })

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        target_url=scan.target_url,
        findings_json=json.dumps(findings_data, indent=2),
    )

    # Load chat history
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
