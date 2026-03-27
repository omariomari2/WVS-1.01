from pathlib import Path

from app.config import settings
from app.services import local_repo


def test_resolve_repo_path_matches_expected_directory_name(tmp_path, monkeypatch) -> None:
    repo_dir = tmp_path / "WVS-1.01"
    (repo_dir / ".git").mkdir(parents=True)

    monkeypatch.setattr(settings, "local_repos_dir", str(tmp_path))

    resolved = local_repo.resolve_repo_path("WVS-1.01", "omariomari2")
    assert resolved == repo_dir.resolve()


def test_resolve_repo_path_falls_back_to_origin_remote_match(tmp_path, monkeypatch) -> None:
    repo_dir = tmp_path / "VenomAI-main"
    (repo_dir / ".git").mkdir(parents=True)

    monkeypatch.setattr(settings, "local_repos_dir", str(tmp_path))

    def fake_origin_url(path: Path) -> str | None:
        if path == repo_dir:
            return "git@github.com:omariomari2/WVS-1.01.git"
        return None

    monkeypatch.setattr("app.services.local_repo._origin_url", fake_origin_url)

    resolved = local_repo.resolve_repo_path("WVS-1.01", "omariomari2")
    assert resolved == repo_dir.resolve()


def test_resolve_repo_path_respects_owner_when_matching_origin(tmp_path, monkeypatch) -> None:
    repo_dir = tmp_path / "VenomAI-main"
    (repo_dir / ".git").mkdir(parents=True)

    monkeypatch.setattr(settings, "local_repos_dir", str(tmp_path))
    monkeypatch.setattr(
        "app.services.local_repo._origin_url",
        lambda _path: "https://github.com/someone-else/WVS-1.01.git",
    )

    resolved = local_repo.resolve_repo_path("WVS-1.01", "omariomari2")
    assert resolved is None
