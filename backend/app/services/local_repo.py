from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
import re

from app.config import settings

PLATFORM_IS_WINDOWS = sys.platform == "win32"


def resolve_repo_path(repo_name: str, repo_owner: str | None = None) -> Path | None:
    if not settings.local_repos_dir:
        return None
    base = Path(settings.local_repos_dir).expanduser()
    if not base.is_dir():
        return None
    candidates = [base / repo_name, base / f"{repo_name}-main", base / f"{repo_name}-master"]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / ".git").exists():
            return candidate.resolve()
    for child in base.iterdir():
        if not child.is_dir():
            continue
        if not (child / ".git").exists():
            continue
        owner_repo = _extract_owner_repo(_origin_url(child) or "")
        if not owner_repo:
            continue
        owner, name = owner_repo
        if name.lower() != repo_name.lower():
            continue
        if repo_owner and owner.lower() != repo_owner.lower():
            continue
        return child.resolve()
    return None


def read_file(repo_path: Path, file_path: str, ref: str | None = None) -> str | None:
    if ref:
        result = subprocess.run(
            ["git", "show", f"{ref}:{file_path}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return result.stdout
        return None
    target = repo_path / file_path
    if target.is_file():
        return target.read_text(encoding="utf-8", errors="replace")
    return None


def read_file_lines(repo_path: Path, file_path: str, center_line: int, context: int = 5) -> str | None:
    content = read_file(repo_path, file_path)
    if content is None:
        return None
    lines = content.splitlines()
    start = max(0, center_line - context - 1)
    end = min(len(lines), center_line + context)
    numbered = [f"{i + 1:>4} | {lines[i]}" for i in range(start, end)]
    return "\n".join(numbered)


def get_current_branch(repo_path: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def write_prompt_file(repo_path: Path, finding_id: str, prompt: str) -> Path:
    prompts_dir = repo_path / ".venomai-prompts"
    prompts_dir.mkdir(exist_ok=True)
    prompt_path = prompts_dir / f"fix-{finding_id}.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def launch_claude_in_terminal(repo_path: Path, prompt_path: Path) -> None:
    if not PLATFORM_IS_WINDOWS:
        raise RuntimeError("Claude launch is currently supported only on Windows.")
    if not repo_path.is_dir():
        raise RuntimeError(f"Local repo path not found: {repo_path}")
    if not prompt_path.is_file():
        raise RuntimeError(f"Prompt file not found: {prompt_path}")
    if shutil.which("claude") is None:
        raise RuntimeError("Claude Code CLI not found on PATH.")

    repo_literal = _powershell_literal(str(repo_path))
    prompt_literal = _powershell_literal(str(prompt_path))
    command = (
        f"Set-Location -LiteralPath '{repo_literal}'; "
        f"$prompt = Get-Content -Raw -LiteralPath '{prompt_literal}'; "
        "claude $prompt"
    )

    subprocess.Popen(
        ["powershell.exe", "-NoExit", "-Command", command],
        cwd=str(repo_path),
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )


def _powershell_literal(value: str) -> str:
    return value.replace("'", "''")


def _origin_url(repo_path: Path) -> str | None:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _extract_owner_repo(remote_url: str) -> tuple[str, str] | None:
    if not remote_url:
        return None
    normalized = remote_url.strip().rstrip("/")
    match = re.search(
        r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
        normalized,
        re.IGNORECASE,
    )
    if not match:
        return None
    owner = match.group("owner")
    repo = match.group("repo")
    if not owner or not repo:
        return None
    return owner, repo
