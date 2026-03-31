from __future__ import annotations

from pathlib import Path

import anthropic
import httpx
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


async def send_to_claude(db: AsyncSession | None, scan: Scan, finding: Finding) -> dict:
    repo_path = await _ensure_local_repo_path(db, scan)

    if not repo_path:
        return {
            "success": False,
            "action": "send_to_claude",
            "finding_id": finding.id,
            "message": "This PR is not linked to a local repository.",
        }
    if not finding.file_path:
        return {
            "success": False,
            "action": "send_to_claude",
            "finding_id": finding.id,
            "message": "This finding is missing a target file path.",
        }

    target_path = repo_path / finding.file_path
    if not target_path.is_file():
        return {
            "success": False,
            "action": "send_to_claude",
            "finding_id": finding.id,
            "message": f"Target file not found in the local repo: {finding.file_path}",
        }

    prompt = await _build_claude_prompt(scan, finding)
    prompt_path = local_repo.write_prompt_file(repo_path, finding.id, prompt)

    try:
        local_repo.launch_claude_in_terminal(repo_path, prompt_path)
    except Exception as exc:
        return {
            "success": False,
            "action": "send_to_claude",
            "finding_id": finding.id,
            "content": prompt,
            "message": f"Could not launch Claude Code: {exc}",
        }

    return {
        "success": True,
        "action": "send_to_claude",
        "finding_id": finding.id,
        "content": prompt,
        "message": f"Claude Code opened in a new terminal using {prompt_path.name}.",
    }


async def pr_comment_ai(db: AsyncSession | None, scan: Scan, finding: Finding) -> dict:
    metadata_error = _comment_metadata_error(scan, finding.id, "pr_comment_ai")
    if metadata_error:
        return metadata_error

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
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
            "content": _build_comment_context(finding),
        }],
    )

    comment_body = response.content[0].text.strip()
    return await _post_pr_comment(
        scan,
        finding,
        comment_body,
        action="pr_comment_ai",
        issue_header=_issue_header(finding),
        failure_prefix="Generated comment but failed to post",
    )


async def pr_comment_manual(
    db: AsyncSession | None, scan: Scan, finding: Finding, comment: str
) -> dict:
    metadata_error = _comment_metadata_error(scan, finding.id, "pr_comment_manual")
    if metadata_error:
        return metadata_error

    comment_body = comment.strip()
    if not comment_body:
        return {
            "success": False,
            "action": "pr_comment_manual",
            "finding_id": finding.id,
            "message": "Comment cannot be empty.",
        }

    return await _post_pr_comment(
        scan,
        finding,
        comment_body,
        action="pr_comment_manual",
        failure_prefix="Failed to post comment",
    )


def _comment_metadata_error(scan: Scan, finding_id: str, action: str) -> dict | None:
    if scan.repo_owner and scan.repo_name and scan.pr_number:
        return None
    return {
        "success": False,
        "action": action,
        "finding_id": finding_id,
        "message": "Missing PR metadata to post a comment.",
    }


async def _post_pr_comment(
    scan: Scan,
    finding: Finding,
    comment_body: str,
    *,
    action: str,
    issue_header: str | None = None,
    failure_prefix: str,
) -> dict:
    try:
        if finding.file_path and finding.line_number:
            commit_id = finding.commit_sha or scan.head_sha
            try:
                if not commit_id:
                    raise RuntimeError(
                        "Missing PR head commit SHA required for inline review comments."
                    )
                await github_client.post_review_comment(
                    scan.repo_owner,
                    scan.repo_name,
                    scan.pr_number,
                    comment_body,
                    commit_id,
                    finding.file_path,
                    finding.line_number,
                )
            except Exception as inline_exc:
                if _should_fallback_to_issue_comment(inline_exc):
                    fallback_body = _build_fallback_issue_body(
                        comment_body,
                        finding,
                        issue_header=issue_header,
                    )
                    try:
                        await github_client.post_issue_comment(
                            scan.repo_owner,
                            scan.repo_name,
                            scan.pr_number,
                            fallback_body,
                        )
                        return {
                            "success": True,
                            "action": action,
                            "finding_id": finding.id,
                            "content": comment_body,
                            "message": (
                                "Inline review comment could not be posted. "
                                "Posted as a general PR comment instead."
                            ),
                        }
                    except Exception as fallback_exc:
                        return {
                            "success": False,
                            "action": action,
                            "finding_id": finding.id,
                            "content": comment_body,
                            "message": (
                                f"{failure_prefix}: inline review comment failed "
                                f"({_github_error_message(inline_exc)}); fallback PR "
                                f"comment also failed ({_github_error_message(fallback_exc)})."
                            ),
                        }
                return {
                    "success": False,
                    "action": action,
                    "finding_id": finding.id,
                    "content": comment_body,
                    "message": f"{failure_prefix}: {_github_error_message(inline_exc)}",
                }
        else:
            issue_body = comment_body
            if issue_header:
                issue_body = f"{issue_header}\n\n{comment_body}"
            await github_client.post_issue_comment(
                scan.repo_owner,
                scan.repo_name,
                scan.pr_number,
                issue_body,
            )
        return {
            "success": True,
            "action": action,
            "finding_id": finding.id,
            "content": comment_body,
            "message": "Comment posted on PR.",
        }
    except Exception as exc:
        return {
            "success": False,
            "action": action,
            "finding_id": finding.id,
            "content": comment_body,
            "message": f"{failure_prefix}: {_github_error_message(exc)}",
        }


def _issue_header(finding: Finding) -> str:
    return f"**{finding.severity}: {finding.title}**"


def _should_fallback_to_issue_comment(exc: Exception) -> bool:
    if not isinstance(exc, httpx.HTTPStatusError):
        return False
    return exc.response.status_code in {403, 422}


def _build_fallback_issue_body(
    comment_body: str,
    finding: Finding,
    *,
    issue_header: str | None,
) -> str:
    location = finding.file_path or "unknown-file"
    if finding.line_number:
        location = f"{location}:{finding.line_number}"
    header = f"{issue_header}\n\n" if issue_header else ""
    return (
        f"{header}{comment_body}\n\n"
        f"_Inline target fallback. Original location: `{location}`._"
    )


def _github_error_message(exc: Exception) -> str:
    if not isinstance(exc, httpx.HTTPStatusError):
        return str(exc)

    status = exc.response.status_code
    message = ""
    detail = ""
    try:
        payload = exc.response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        message = str(payload.get("message") or "").strip()
        raw_errors = payload.get("errors")
        if isinstance(raw_errors, list) and raw_errors:
            parts: list[str] = []
            for item in raw_errors[:3]:
                if isinstance(item, dict):
                    code = str(item.get("code") or "").strip()
                    item_message = str(item.get("message") or "").strip()
                    if code and item_message:
                        parts.append(f"{code}: {item_message}")
                    elif code or item_message:
                        parts.append(code or item_message)
                else:
                    parts.append(str(item))
            if parts:
                detail = "; ".join(parts)

    bits = [f"GitHub API {status}"]
    if message:
        bits.append(message)
    if detail:
        bits.append(detail)
    if status == 401:
        bits.append(
            "Check GITHUB_TOKEN. The token may be missing, expired, or invalid for this repository."
        )
    elif status == 403:
        bits.append(
            "Check GITHUB_TOKEN repository access and scopes. "
            "Inline comments require Pull requests (write); PR comments require Issues (write)."
        )
    elif status == 422:
        bits.append(
            "GitHub rejected the inline location. "
            "Verify the file path and line exist on the current PR diff."
        )
    return " - ".join(bits)


def _build_comment_context(finding: Finding) -> str:
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
    return "\n".join(context_parts)


async def _build_claude_prompt(scan: Scan, finding: Finding) -> str:
    code_snippet = finding.code_snippet
    if not code_snippet and scan.local_repo_path and finding.file_path:
        repo_path = Path(scan.local_repo_path)
        line = finding.line_number or 1
        code_snippet = local_repo.read_file_lines(repo_path, finding.file_path, line, context=10)

    lang = _language_from_path(finding.file_path or "")
    parts = [
        "Fix this security finding in the local repository.",
        "",
        f"Repository: {scan.repo_owner}/{scan.repo_name}" if scan.repo_owner and scan.repo_name else "Repository: local checkout",
        f"File: {finding.file_path or 'unknown'}",
    ]
    if finding.line_number:
        parts.append(f"Line: {finding.line_number}")
    parts.extend(
        [
            f"Severity: {finding.severity}",
            f"Issue: {finding.title} ({finding.owasp_category} - {finding.owasp_name})",
        ]
    )
    if finding.cwe:
        parts.append(f"CWE: {finding.cwe}")

    if code_snippet:
        parts.extend(
            [
                "",
                "Code context:",
                f"```{lang}",
                code_snippet,
                "```",
            ]
        )

    parts.extend(
        [
            "",
            f"What is wrong: {finding.description}",
        ]
    )
    if finding.evidence:
        parts.append(f"Evidence: {finding.evidence}")
    parts.extend(
        [
            f"How to fix: {finding.remediation}",
            "",
            "Update the repository in place. Preserve existing behavior, keep the fix scoped to this finding, and explain any assumptions before editing code.",
        ]
    )

    return "\n".join(parts)


async def _ensure_local_repo_path(db: AsyncSession | None, scan: Scan) -> Path | None:
    if scan.local_repo_path:
        repo_path = Path(scan.local_repo_path)
        if repo_path.is_dir():
            return repo_path

    if not scan.repo_name:
        return None

    repo_path = local_repo.resolve_repo_path(scan.repo_name, scan.repo_owner)
    if not repo_path:
        return None

    scan.local_repo_path = str(repo_path)
    if db is not None:
        await db.commit()
        await db.refresh(scan)
    return repo_path
