from __future__ import annotations

import io
import json
import re
import zipfile
from typing import Any

import httpx

from app.config import settings

API_BASE = "https://api.github.com"


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if settings.github_token:
        h["Authorization"] = f"Bearer {settings.github_token}"
    return h


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=API_BASE,
        headers=_headers(),
        timeout=30,
        follow_redirects=True,
    )


def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if not match:
        raise ValueError(f"Invalid GitHub PR URL: {pr_url}")
    return match.group(1), match.group(2), int(match.group(3))


async def get_pr(owner: str, repo: str, pr_number: int) -> dict[str, Any]:
    async with _client() as c:
        resp = await c.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        resp.raise_for_status()
        return resp.json()


async def get_pr_commits(owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
    commits: list[dict[str, Any]] = []
    page = 1
    async with _client() as c:
        while True:
            resp = await c.get(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/commits",
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            commits.extend(batch)
            page += 1
    return commits


async def get_pr_files(owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    page = 1
    async with _client() as c:
        while True:
            resp = await c.get(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            files.extend(batch)
            page += 1
    return files


async def get_file_content(owner: str, repo: str, path: str, ref: str) -> str:
    async with _client() as c:
        resp = await c.get(
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
            headers={**_headers(), "Accept": "application/vnd.github.raw+json"},
        )
        resp.raise_for_status()
        return resp.text


async def download_workflow_artifacts(
    owner: str, repo: str, head_sha: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    async with _client() as c:
        runs_resp = await c.get(
            f"/repos/{owner}/{repo}/actions/runs",
            params={"head_sha": head_sha, "event": "pull_request", "per_page": 10},
        )
        runs_resp.raise_for_status()
        runs = runs_resp.json().get("workflow_runs", [])

        target_run = None
        for run in runs:
            if "security" in run.get("name", "").lower() or "pr-security" in run.get("name", "").lower():
                target_run = run
                break
        if not target_run and runs:
            target_run = runs[0]
        if not target_run:
            return None, None

        arts_resp = await c.get(
            f"/repos/{owner}/{repo}/actions/runs/{target_run['id']}/artifacts",
            params={"per_page": 50},
        )
        arts_resp.raise_for_status()
        artifacts = arts_resp.json().get("artifacts", [])

        base_findings = None
        pr_findings = None

        for art in artifacts:
            name = art.get("name", "")
            if name in ("base-findings", "pr-findings"):
                dl_resp = await c.get(
                    f"/repos/{owner}/{repo}/actions/artifacts/{art['id']}/zip",
                )
                dl_resp.raise_for_status()
                zf = zipfile.ZipFile(io.BytesIO(dl_resp.content))
                for fname in zf.namelist():
                    if fname.endswith(".json"):
                        data = json.loads(zf.read(fname))
                        if name == "base-findings":
                            base_findings = data
                        else:
                            pr_findings = data
                        break

        return base_findings, pr_findings


async def post_review_comment(
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    path: str,
    line: int,
    side: str = "RIGHT",
) -> dict[str, Any]:
    async with _client() as c:
        resp = await c.post(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
            json={"body": body, "path": path, "line": line, "side": side},
        )
        resp.raise_for_status()
        return resp.json()


async def post_review(
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    event: str,
    comments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"body": body, "event": event}
    if comments:
        payload["comments"] = comments
    async with _client() as c:
        resp = await c.post(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def post_issue_comment(
    owner: str, repo: str, issue_number: int, body: str
) -> dict[str, Any]:
    async with _client() as c:
        resp = await c.post(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        resp.raise_for_status()
        return resp.json()
