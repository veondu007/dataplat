import os

from app.core.config import _repo_root, settings
from app.main import app

REPO_ROOT = _repo_root()
VERSION_FILE = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def test_version_from_version_file():
    expected = os.environ.get("DATAPLAT_VERSION") or VERSION_FILE
    assert settings.version == expected


def test_repo_root_points_to_monorepo_root():
    assert (REPO_ROOT / "VERSION").is_file()
    assert (REPO_ROOT / "apps").is_dir()
    assert (REPO_ROOT / "docs").is_dir()


def test_app_version_matches_settings():
    assert app.version == settings.version
