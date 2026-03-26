from __future__ import annotations

import json
from pathlib import Path

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Finding, Scan
from app.services import github_client, local_repo


def _language_from_path(file_path: str) -> str:
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".tsx": "tsx", ".jsx": "jsx", ".java": "java", ".go": "go",
        ".rs": "rust", ".rb": "ruby", ".php": "php", ".c": "c",
        ".cpp": "cpp", ".cs": "csharp", ".yml": "yaml", ".yaml": "yaml",
        ".json": "json", ".sql": "sql", ".sh": "bash",
    }
    suffix = Path(file_path).suffix.lower()
    return ext_map.get(suffix, "")


async def send_to_cursor(db: AsyncSession, scan: Scan, finding: Finding) -> dict:
    prompt = await _build_cursor_prompt(scan, finding)

    local_repo.copy_to_clipboard(prompt)

    if finding.file_path and scan.local_repo_path:
        repo_path = Path(scan.local_repo_path)
        line = finding.line_number or 1
        await local_repo.open_in_cursor(repo_path, finding.file_path, line)

    if scan.local_repo_path and finding.id:
        repo_path = Path(scan.local_repo_path)
        local_repo.write_prompt_file(repo_path, finding.id, prompt)

    return {
        "success": True,
        "action": "send_to_cursor",
        "finding_id": finding.id,
        "content": prompt,
        "message": "Fix prompt copied to clipboard and file opened in Cursor.",
    }


async def apply_fix(db: AsyncSession, scan: Scan, finding: Finding) -> dict:
    if not scan.local_repo_path or not finding.file_path:
        return {
            "success": False,
            "action": "apply_fix",
            "finding_id": finding.id,
            "message": "No local repo path or file path available.",
        }

    repo_path = Path(scan.local_repo_path)
    file_content = local_repo.read_file(repo_path, finding.file_path)
    if file_content is None:
        return {
            "success": False,
            "action": "apply_fix",
            "finding_id": finding.id,
            "message": f"Cannot read file: {finding.file_path}",
        }

    lines = file_content.splitlines()
    if finding.line_number:
        start = max(0, finding.line_number - 6)
        end = min(len(lines), finding.line_number + 5)
    else:
        start = 0
        end = len(lines)

    original_block = "\n".join(lines[start:end])
    lang = _language_from_path(finding.file_path)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system="You are a security-focused code fixer. Return ONLY the fixed replacement code. No explanations, no markdown fences, no comments. Just the corrected code that replaces the original block.",
        messages=[{
            "role": "user",
            "content": (
                f"Fix this {finding.severity} security vulnerability.\n\n"
                f"File: {finding.file_path}\n"
                f"Issue: {finding.title}\n"
                f"Description: {finding.description}\n"
                f"Remediation: {finding.remediation}\n\n"
                f"Original code (lines {start + 1}-{end}):\n"
                f"```{lang}\n{original_block}\n```\n\n"
                f"Return ONLY the fixed version of these exact lines."
            ),
        }],
    )

    patched_block = response.content[0].text.strip()
    if patched_block.startswith("```"):
        first_nl = patched_block.index("\n")
        patched_block = patched_block[first_nl + 1:]
    if patched_block.endswith("```"):
        patched_block = patched_block[:-3].rstrip()

    diff_preview = _build_diff(original_block, patched_block, finding.file_path, start + 1)

    applied = local_repo.apply_patch(repo_path, finding.file_path, original_block, patched_block)

    return {
        "success": applied,
        "action": "apply_fix",
        "finding_id": finding.id,
        "content": patched_block,
        "diff_preview": diff_preview,
        "message": "Fix applied to local file." if applied else "Could not apply patch — original code block not found in file.",
    }


async def pr_comment(db: AsyncSession, scan: Scan, finding: Finding) -> dict:
    if not scan.repo_owner or not scan.repo_name or not scan.pr_number:
        return {
            "success": False,
            "action": "pr_comment",
            "finding_id": finding.id,
            "message": "Missing PR metadata to post a comment.",
        }

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    context_parts = [
        f"Severity: {finding.severity}",
        f"OWASP: {finding.owasp_category} - {finding.owasp_name}",
    ]
    if finding.cwe:
        context_parts.append(f"CWE: {finding.cwe}")
    context_parts.append(f"Description: {finding.description}")
    if finding.evidence:
        context_parts.append(f"Evidence: {finding.evidence}")
    context_parts.append(f"Remediation: {finding.remediation}")
    if finding.code_snippet:
        context_parts.append(f"Code context:\n{finding.code_snippet}")

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=(
            "You are a security reviewer posting an inline comment on a GitHub PR. "
            "Write a concise, actionable comment that explains the vulnerability, "
            "its impact, and gives a specific fix suggestion. Use GitHub markdown. "
            "Keep it under 200 words."
        ),
        messages=[{
            "role": "user",
            "content": "\n".join(context_parts),
        }],
    )

    comment_body = response.content[0].text.strip()

    try:
        if finding.file_path and finding.line_number:
            await github_client.post_review_comment(
                scan.repo_owner, scan.repo_name, scan.pr_number,
                comment_body, finding.file_path, finding.line_number,
            )
        else:
            await github_client.post_issue_comment(
                scan.repo_owner, scan.repo_name, scan.pr_number,
                f"**{finding.severity}: {finding.title}**\n\n{comment_body}",
            )
        return {
            "success": True,
            "action": "pr_comment",
            "finding_id": finding.id,
            "content": comment_body,
            "message": "Comment posted on PR.",
        }
    except Exception as e:
        return {
            "success": False,
            "action": "pr_comment",
            "finding_id": finding.id,
            "content": comment_body,
            "message": f"Generated comment but failed to post: {e}",
        }


async def full_review(db: AsyncSession, scan: Scan, findings: list[Finding]) -> dict:
    if not scan.repo_owner or not scan.repo_name or not scan.pr_number:
        return {
            "success": False,
            "action": "full_review",
            "finding_id": "",
            "message": "Missing PR metadata to post a review.",
        }

    findings_summary = []
    for f in findings:
        entry = f"- [{f.severity}] {f.title}"
        if f.file_path:
            entry += f" in `{f.file_path}"
            if f.line_number:
                entry += f":{f.line_number}"
            entry += "`"
        entry += f"\n  {f.description}"
        if f.remediation:
            entry += f"\n  Fix: {f.remediation}"
        findings_summary.append(entry)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=(
            "You are a security reviewer writing a comprehensive GitHub PR review. "
            "Summarize the findings, explain the overall security posture, "
            "and give prioritized recommendations. Use GitHub markdown."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"PR: {scan.pr_title or scan.pr_url}\n"
                f"Branch: {scan.pr_branch} -> {scan.base_branch}\n"
                f"Total findings: {len(findings)}\n\n"
                + "\n\n".join(findings_summary)
            ),
        }],
    )

    review_body = response.content[0].text.strip()

    has_blocking = any(f.severity in ("Critical", "High") for f in findings)
    event = "REQUEST_CHANGES" if has_blocking else "COMMENT"

    inline_comments = []
    for f in findings:
        if f.file_path and f.line_number:
            inline_comments.append({
                "path": f.file_path,
                "line": f.line_number,
                "side": "RIGHT",
                "body": f"**{f.severity}: {f.title}**\n{f.description}\n\n**Fix:** {f.remediation}",
            })

    try:
        await github_client.post_review(
            scan.repo_owner, scan.repo_name, scan.pr_number,
            review_body, event,
            inline_comments if inline_comments else None,
        )
        return {
            "success": True,
            "action": "full_review",
            "finding_id": "",
            "content": review_body,
            "message": f"Security review posted ({event}).",
        }
    except Exception as e:
        return {
            "success": False,
            "action": "full_review",
            "finding_id": "",
            "content": review_body,
            "message": f"Generated review but failed to post: {e}",
        }


async def _build_cursor_prompt(scan: Scan, finding: Finding) -> str:
    code_snippet = finding.code_snippet
    if not code_snippet and scan.local_repo_path and finding.file_path:
        repo_path = Path(scan.local_repo_path)
        line = finding.line_number or 1
        code_snippet = local_repo.read_file_lines(repo_path, finding.file_path, line, context=10)

    lang = _language_from_path(finding.file_path or "")
    parts = [
        f"Fix a {finding.severity} security vulnerability in @{finding.file_path}",
    ]
    if finding.line_number:
        parts[0] += f" at line {finding.line_number}"
    parts[0] += "."

    parts.append("")
    parts.append(f"**Issue:** {finding.title} ({finding.owasp_category} - {finding.owasp_name})")
    if finding.cwe:
        parts.append(f"**CWE:** {finding.cwe}")

    if code_snippet:
        parts.append("")
        parts.append("**Current code:**")
        parts.append(f"```{lang}")
        parts.append(code_snippet)
        parts.append("```")

    parts.append("")
    parts.append(f"**What's wrong:** {finding.description}")

    if finding.evidence:
        parts.append("")
        parts.append(f"**Evidence:** {finding.evidence}")

    parts.append("")
    parts.append(f"**How to fix:** {finding.remediation}")

    parts.append("")
    parts.append("Apply the fix in place. Preserve existing functionality. Do not add comments.")

    return "\n".join(parts)


def _build_diff(original: str, patched: str, file_path: str, start_line: int) -> str:
    orig_lines = original.splitlines()
    patch_lines = patched.splitlines()
    diff_lines = [f"--- a/{file_path}", f"+++ b/{file_path}"]
    diff_lines.append(f"@@ -{start_line},{len(orig_lines)} +{start_line},{len(patch_lines)} @@")
    for line in orig_lines:
        diff_lines.append(f"-{line}")
    for line in patch_lines:
        diff_lines.append(f"+{line}")
    return "\n".join(diff_lines)
