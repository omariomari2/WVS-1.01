from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

from app.config import settings

PLATFORM_IS_WINDOWS = sys.platform == "win32"


def resolve_repo_path(repo_name: str) -> Path | None:
    if not settings.local_repos_dir:
        return None
    base = Path(settings.local_repos_dir)
    candidates = [base / repo_name, base / f"{repo_name}-main", base / f"{repo_name}-master"]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / ".git").exists():
            return candidate.resolve()
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


def apply_patch(repo_path: Path, file_path: str, original_lines: str, patched_lines: str) -> bool:
    target = repo_path / file_path
    if not target.is_file():
        return False
    content = target.read_text(encoding="utf-8", errors="replace")
    if original_lines not in content:
        return False
    backup = target.with_suffix(target.suffix + ".venomai.bak")
    shutil.copy2(target, backup)
    new_content = content.replace(original_lines, patched_lines, 1)
    target.write_text(new_content, encoding="utf-8")
    return True


async def open_in_cursor(repo_path: Path, file_path: str, line: int) -> bool:
    abs_path = repo_path / file_path
    if not abs_path.is_file():
        return False
    cmd = ["cursor", "--goto", f"{abs_path}:{line}"]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    return proc.returncode == 0


def copy_to_clipboard(text: str) -> bool:
    if PLATFORM_IS_WINDOWS:
        proc = subprocess.run(
            ["clip.exe"],
            input=text,
            encoding="utf-8",
            capture_output=True,
        )
        return proc.returncode == 0
    if shutil.which("pbcopy"):
        proc = subprocess.run(["pbcopy"], input=text, encoding="utf-8", capture_output=True)
        return proc.returncode == 0
    if shutil.which("xclip"):
        proc = subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text,
            encoding="utf-8",
            capture_output=True,
        )
        return proc.returncode == 0
    return False


def write_prompt_file(repo_path: Path, finding_id: str, prompt: str) -> Path:
    prompts_dir = repo_path / ".venomai-prompts"
    prompts_dir.mkdir(exist_ok=True)
    prompt_path = prompts_dir / f"fix-{finding_id}.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path
