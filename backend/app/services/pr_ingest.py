from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Finding, PrCommit, Scan
from app.sast.base import ScanSnapshot
from app.sast.diff_engine import compare_findings
from app.scanner.severity import Severity
from app.services import github_client, local_repo


async def run_pr_ingest(scan_id: str, pr_url: str):
    owner, repo_name, pr_number = github_client.parse_pr_url(pr_url)

    async with async_session() as db:
        scan = await db.get(Scan, scan_id)
        if not scan:
            return

        scan.status = "running"
        scan.progress = 0.1
        scan.current_module = "Fetching PR metadata"
        await db.commit()

        try:
            pr_data = await github_client.get_pr(owner, repo_name, pr_number)

            scan.pr_title = pr_data.get("title", "")
            scan.pr_branch = pr_data.get("head", {}).get("ref", "")
            scan.base_branch = pr_data.get("base", {}).get("ref", "")
            scan.head_sha = pr_data.get("head", {}).get("sha", "")
            scan.target_url = pr_url
            await db.commit()

            repo_path = local_repo.resolve_repo_path(repo_name)
            if repo_path:
                scan.local_repo_path = str(repo_path)
                await db.commit()

            scan.progress = 0.2
            scan.current_module = "Fetching PR commits"
            await db.commit()

            commits_data = await github_client.get_pr_commits(owner, repo_name, pr_number)
            for c in commits_data:
                commit_info = c.get("commit", {})
                author_info = commit_info.get("author", {}) or {}
                pr_commit = PrCommit(
                    scan_id=scan_id,
                    sha=c.get("sha", ""),
                    message=commit_info.get("message", ""),
                    author=author_info.get("name", "unknown"),
                )
                db.add(pr_commit)
            await db.commit()

            scan.progress = 0.3
            scan.current_module = "Fetching changed files"
            await db.commit()

            pr_files = await github_client.get_pr_files(owner, repo_name, pr_number)
            file_patches: dict[str, str] = {}
            for f in pr_files:
                file_patches[f.get("filename", "")] = f.get("patch", "")

            scan.progress = 0.5
            scan.current_module = "Downloading SAST artifacts"
            await db.commit()

            base_snapshot_data, head_snapshot_data = await github_client.download_workflow_artifacts(
                owner, repo_name, scan.head_sha or ""
            )

            all_findings: list[dict] = []

            if base_snapshot_data and head_snapshot_data:
                scan.progress = 0.7
                scan.current_module = "Comparing findings"
                await db.commit()

                base_snapshot = ScanSnapshot.from_dict(base_snapshot_data)
                head_snapshot = ScanSnapshot.from_dict(head_snapshot_data)
                diff = compare_findings(
                    base_snapshot.findings, head_snapshot.findings, Severity.HIGH
                )

                for sf in diff.new_findings:
                    code_snippet = None
                    if repo_path and sf.file_path and sf.line:
                        code_snippet = local_repo.read_file_lines(
                            repo_path, sf.file_path, sf.line, context=5
                        )
                    elif sf.file_path and sf.line and scan.head_sha:
                        try:
                            content = await github_client.get_file_content(
                                owner, repo_name, sf.file_path, scan.head_sha
                            )
                            lines = content.splitlines()
                            start = max(0, sf.line - 6)
                            end = min(len(lines), sf.line + 5)
                            numbered = [f"{i + 1:>4} | {lines[i]}" for i in range(start, end)]
                            code_snippet = "\n".join(numbered)
                        except Exception:
                            pass

                    diff_hunk = file_patches.get(sf.file_path or "", None)

                    all_findings.append({
                        "owasp_category": sf.owasp or sf.category,
                        "owasp_name": sf.title,
                        "severity": sf.severity.value if hasattr(sf.severity, "value") else str(sf.severity),
                        "title": sf.title,
                        "description": sf.message,
                        "evidence": sf.evidence,
                        "url": pr_url,
                        "remediation": sf.remediation or "",
                        "confidence": sf.confidence.value if hasattr(sf.confidence, "value") else str(sf.confidence),
                        "file_path": sf.file_path,
                        "line_number": sf.line,
                        "commit_sha": None,
                        "code_snippet": code_snippet,
                        "diff_hunk": _truncate(diff_hunk, 2000) if diff_hunk else None,
                        "rule_id": sf.rule_id,
                        "cwe": sf.cwe,
                    })
            elif head_snapshot_data:
                head_snapshot = ScanSnapshot.from_dict(head_snapshot_data)
                for sf in head_snapshot.findings:
                    code_snippet = None
                    if repo_path and sf.file_path and sf.line:
                        code_snippet = local_repo.read_file_lines(
                            repo_path, sf.file_path, sf.line, context=5
                        )

                    all_findings.append({
                        "owasp_category": sf.owasp or sf.category,
                        "owasp_name": sf.title,
                        "severity": sf.severity.value if hasattr(sf.severity, "value") else str(sf.severity),
                        "title": sf.title,
                        "description": sf.message,
                        "evidence": sf.evidence,
                        "url": pr_url,
                        "remediation": sf.remediation or "",
                        "confidence": sf.confidence.value if hasattr(sf.confidence, "value") else str(sf.confidence),
                        "file_path": sf.file_path,
                        "line_number": sf.line,
                        "commit_sha": None,
                        "code_snippet": code_snippet,
                        "diff_hunk": _truncate(file_patches.get(sf.file_path or "", ""), 2000) or None,
                        "rule_id": sf.rule_id,
                        "cwe": sf.cwe,
                    })
            else:
                scan.progress = 0.7
                scan.current_module = "No SAST artifacts found — importing PR file changes"
                await db.commit()

                for f in pr_files:
                    filename = f.get("filename", "")
                    patch = f.get("patch", "")
                    if not patch:
                        continue
                    all_findings.append({
                        "owasp_category": "PR",
                        "owasp_name": "Changed File",
                        "severity": "Informational",
                        "title": f"Changed: {filename}",
                        "description": f"File was modified in this PR ({f.get('additions', 0)} additions, {f.get('deletions', 0)} deletions).",
                        "evidence": None,
                        "url": pr_url,
                        "remediation": "Review the changes for security implications.",
                        "confidence": "Low",
                        "file_path": filename,
                        "line_number": None,
                        "commit_sha": None,
                        "code_snippet": None,
                        "diff_hunk": _truncate(patch, 2000),
                        "rule_id": None,
                        "cwe": None,
                    })

            scan.progress = 0.9
            scan.current_module = "Persisting findings"
            await db.commit()

            for fd in all_findings:
                finding = Finding(
                    scan_id=scan_id,
                    owasp_category=fd["owasp_category"],
                    owasp_name=fd["owasp_name"],
                    severity=fd["severity"],
                    title=fd["title"],
                    description=fd["description"],
                    evidence=fd["evidence"],
                    url=fd["url"],
                    remediation=fd["remediation"],
                    confidence=fd["confidence"],
                    file_path=fd["file_path"],
                    line_number=fd["line_number"],
                    commit_sha=fd["commit_sha"],
                    code_snippet=fd["code_snippet"],
                    diff_hunk=fd["diff_hunk"],
                    rule_id=fd["rule_id"],
                    cwe=fd["cwe"],
                )
                db.add(finding)

            scan.status = "completed"
            scan.progress = 1.0
            scan.current_module = None
            scan.total_findings = len(all_findings)
            scan.completed_at = datetime.now(timezone.utc).isoformat()
            await db.commit()

        except Exception as e:
            scan.status = "failed"
            scan.error_message = str(e)
            scan.completed_at = datetime.now(timezone.utc).isoformat()
            await db.commit()


def _truncate(text: str | None, max_len: int) -> str | None:
    if not text:
        return None
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n... (truncated)"
