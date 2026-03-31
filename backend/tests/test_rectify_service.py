import asyncio
from pathlib import Path
from types import SimpleNamespace

import httpx

from app.models import Finding, Scan
from app.services import rectify_service


def _build_scan(**overrides) -> Scan:
    defaults = {
        "id": "scan-1",
        "target_url": "https://github.com/example/repo/pull/1",
        "status": "completed",
        "scan_type": "pr",
        "repo_owner": "example",
        "repo_name": "repo",
        "pr_number": 1,
        "head_sha": "abc123def456",
        "local_repo_path": None,
    }
    defaults.update(overrides)
    return Scan(**defaults)


def _build_finding(**overrides) -> Finding:
    defaults = {
        "id": "finding-1",
        "scan_id": "scan-1",
        "owasp_category": "A02",
        "owasp_name": "Cryptographic Failures",
        "severity": "High",
        "title": "TLS verification disabled",
        "description": "Outbound requests disable certificate verification.",
        "evidence": "verify=False",
        "url": "https://github.com/example/repo/pull/1",
        "remediation": "Enable TLS verification for outbound HTTP requests.",
        "confidence": "High",
        "created_at": "2026-03-26T00:00:00+00:00",
        "file_path": "backend/app/scanner/http_client.py",
        "line_number": 12,
        "code_snippet": "client = httpx.AsyncClient(verify=False)",
        "diff_hunk": None,
        "rule_id": "insecure-defaults",
        "cwe": "CWE-295",
    }
    defaults.update(overrides)
    return Finding(**defaults)


def test_send_to_claude_launches_terminal_when_local_repo_is_available(tmp_path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    target_path = repo_path / "backend/app/scanner/http_client.py"
    target_path.parent.mkdir(parents=True)
    target_path.write_text("client = httpx.AsyncClient(verify=False)\n", encoding="utf-8")

    launched: dict[str, Path] = {}

    def fake_launch(repo_arg: Path, prompt_arg: Path) -> None:
        launched["repo"] = repo_arg
        launched["prompt"] = prompt_arg

    monkeypatch.setattr("app.services.local_repo.launch_claude_in_terminal", fake_launch)

    result = asyncio.run(
        rectify_service.send_to_claude(
            None,
            _build_scan(local_repo_path=str(repo_path)),
            _build_finding(),
        )
    )

    assert result["success"] is True
    assert result["action"] == "send_to_claude"
    assert launched["repo"] == repo_path
    assert launched["prompt"].is_file()
    assert "Fix this security finding" in launched["prompt"].read_text(encoding="utf-8")


def test_send_to_claude_fails_when_target_file_is_missing(tmp_path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    result = asyncio.run(
        rectify_service.send_to_claude(
            None,
            _build_scan(local_repo_path=str(repo_path)),
            _build_finding(),
        )
    )

    assert result == {
        "success": False,
        "action": "send_to_claude",
        "finding_id": "finding-1",
        "message": "Target file not found in the local repo: backend/app/scanner/http_client.py",
    }


def test_send_to_claude_surfaces_launch_errors(tmp_path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    target_path = repo_path / "backend/app/scanner/http_client.py"
    target_path.parent.mkdir(parents=True)
    target_path.write_text("client = httpx.AsyncClient(verify=False)\n", encoding="utf-8")

    def fake_launch(repo_arg: Path, prompt_arg: Path) -> None:
        raise RuntimeError("Claude Code CLI not found on PATH.")

    monkeypatch.setattr("app.services.local_repo.launch_claude_in_terminal", fake_launch)

    result = asyncio.run(
        rectify_service.send_to_claude(
            None,
            _build_scan(local_repo_path=str(repo_path)),
            _build_finding(),
        )
    )

    assert result["success"] is False
    assert result["action"] == "send_to_claude"
    assert result["message"] == "Could not launch Claude Code: Claude Code CLI not found on PATH."
    assert "Fix this security finding" in (result["content"] or "")


def test_send_to_claude_recovers_missing_local_repo_path(tmp_path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    target_path = repo_path / "backend/app/scanner/http_client.py"
    target_path.parent.mkdir(parents=True)
    target_path.write_text("client = httpx.AsyncClient(verify=False)\n", encoding="utf-8")

    launched: dict[str, Path] = {}

    def fake_resolve(repo_name: str, repo_owner: str | None = None) -> Path:
        assert repo_name == "repo"
        assert repo_owner == "example"
        return repo_path

    def fake_launch(repo_arg: Path, prompt_arg: Path) -> None:
        launched["repo"] = repo_arg
        launched["prompt"] = prompt_arg

    monkeypatch.setattr("app.services.local_repo.resolve_repo_path", fake_resolve)
    monkeypatch.setattr("app.services.local_repo.launch_claude_in_terminal", fake_launch)

    scan = _build_scan(local_repo_path=None)

    result = asyncio.run(
        rectify_service.send_to_claude(
            None,
            scan,
            _build_finding(),
        )
    )

    assert result["success"] is True
    assert scan.local_repo_path == str(repo_path)
    assert launched["repo"] == repo_path
    assert launched["prompt"].is_file()


def test_manual_comment_posts_inline_when_file_context_exists(monkeypatch) -> None:
    posted: dict[str, object] = {}

    async def fake_post_review_comment(
        owner, repo, pr_number, body, commit_id, path, line, side="RIGHT"
    ):
        posted.update(
            {
                "owner": owner,
                "repo": repo,
                "pr_number": pr_number,
                "body": body,
                "commit_id": commit_id,
                "path": path,
                "line": line,
                "side": side,
            }
        )
        return {"ok": True}

    monkeypatch.setattr("app.services.github_client.post_review_comment", fake_post_review_comment)

    result = asyncio.run(
        rectify_service.pr_comment_manual(
            None,
            _build_scan(),
            _build_finding(),
            "Please restore TLS verification here.",
        )
    )

    assert result["success"] is True
    assert posted["body"] == "Please restore TLS verification here."
    assert posted["commit_id"] == _build_scan().head_sha
    assert posted["path"] == "backend/app/scanner/http_client.py"
    assert posted["line"] == 12


def test_manual_comment_falls_back_to_general_pr_comment(monkeypatch) -> None:
    posted: dict[str, object] = {}

    async def fake_post_issue_comment(owner, repo, issue_number, body):
        posted.update(
            {
                "owner": owner,
                "repo": repo,
                "issue_number": issue_number,
                "body": body,
            }
        )
        return {"ok": True}

    monkeypatch.setattr("app.services.github_client.post_issue_comment", fake_post_issue_comment)

    result = asyncio.run(
        rectify_service.pr_comment_manual(
            None,
            _build_scan(),
            _build_finding(file_path=None, line_number=None),
            "Please address this before merge.",
        )
    )

    assert result["success"] is True
    assert posted["body"] == "Please address this before merge."
    assert posted["issue_number"] == 1


def test_ai_comment_preserves_inline_targeting(monkeypatch) -> None:
    posted: dict[str, object] = {}

    async def fake_post_review_comment(
        owner, repo, pr_number, body, commit_id, path, line, side="RIGHT"
    ):
        posted.update(
            {
                "owner": owner,
                "repo": repo,
                "pr_number": pr_number,
                "body": body,
                "commit_id": commit_id,
                "path": path,
                "line": line,
            }
        )
        return {"ok": True}

    class _FakeMessages:
        async def create(self, **kwargs):
            return SimpleNamespace(content=[SimpleNamespace(text="Generated AI review comment")])

    class _FakeAnthropic:
        def __init__(self, api_key: str):
            self.messages = _FakeMessages()

    monkeypatch.setattr("app.services.github_client.post_review_comment", fake_post_review_comment)
    monkeypatch.setattr("app.services.rectify_service.anthropic.AsyncAnthropic", _FakeAnthropic)

    result = asyncio.run(
        rectify_service.pr_comment_ai(
            None,
            _build_scan(),
            _build_finding(),
        )
    )

    assert result["success"] is True
    assert posted["body"] == "Generated AI review comment"
    assert posted["commit_id"] == _build_scan().head_sha
    assert posted["path"] == "backend/app/scanner/http_client.py"
    assert posted["line"] == 12


def test_manual_comment_falls_back_when_inline_comment_is_forbidden(monkeypatch) -> None:
    posted: dict[str, object] = {}

    async def fake_post_review_comment(
        owner, repo, pr_number, body, commit_id, path, line, side="RIGHT"
    ):
        request = httpx.Request("POST", "https://api.github.com/repos/example/repo/pulls/1/comments")
        response = httpx.Response(
            403,
            request=request,
            json={"message": "Resource not accessible by personal access token"},
        )
        raise httpx.HTTPStatusError(
            "Client error '403 Forbidden' for url 'https://api.github.com/repos/example/repo/pulls/1/comments'",
            request=request,
            response=response,
        )

    async def fake_post_issue_comment(owner, repo, issue_number, body):
        posted.update(
            {
                "owner": owner,
                "repo": repo,
                "issue_number": issue_number,
                "body": body,
            }
        )
        return {"ok": True}

    monkeypatch.setattr("app.services.github_client.post_review_comment", fake_post_review_comment)
    monkeypatch.setattr("app.services.github_client.post_issue_comment", fake_post_issue_comment)

    result = asyncio.run(
        rectify_service.pr_comment_manual(
            None,
            _build_scan(),
            _build_finding(),
            "Please restore TLS verification here.",
        )
    )

    assert result["success"] is True
    assert "general PR comment" in result["message"]
    assert "Original location: `backend/app/scanner/http_client.py:12`" in str(posted["body"])


def test_manual_comment_includes_permission_guidance_when_github_returns_403(monkeypatch) -> None:
    async def fake_post_review_comment(
        owner, repo, pr_number, body, commit_id, path, line, side="RIGHT"
    ):
        request = httpx.Request("POST", "https://api.github.com/repos/example/repo/pulls/1/comments")
        response = httpx.Response(
            403,
            request=request,
            json={"message": "Resource not accessible by personal access token"},
        )
        raise httpx.HTTPStatusError("403 Forbidden", request=request, response=response)

    async def fake_post_issue_comment(owner, repo, issue_number, body):
        request = httpx.Request("POST", "https://api.github.com/repos/example/repo/issues/1/comments")
        response = httpx.Response(
            403,
            request=request,
            json={"message": "Resource not accessible by personal access token"},
        )
        raise httpx.HTTPStatusError("403 Forbidden", request=request, response=response)

    monkeypatch.setattr("app.services.github_client.post_review_comment", fake_post_review_comment)
    monkeypatch.setattr("app.services.github_client.post_issue_comment", fake_post_issue_comment)

    result = asyncio.run(
        rectify_service.pr_comment_manual(
            None,
            _build_scan(),
            _build_finding(),
            "Please restore TLS verification here.",
        )
    )

    assert result["success"] is False
    assert "Pull requests (write)" in result["message"]
