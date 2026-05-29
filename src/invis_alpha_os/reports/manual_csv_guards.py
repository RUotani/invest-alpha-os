"""Guards for manual CSV import paths (no secrets)."""

from __future__ import annotations

from pathlib import Path

from invis_alpha_os.config.env_file_loader import is_git_tracked


class ManualCsvPathError(ValueError):
    """Raised when a CSV path is not allowed for import."""


ALLOWED_MANUAL_DATA_SUFFIXES: frozenset[str] = frozenset({".csv", ".tsv", ".txt", ".xlsx"})


def resolve_manual_data_path(data_path: str, *, repo_root: Path) -> Path:
    resolved = Path(data_path).expanduser().resolve()
    if not resolved.is_file():
        raise ManualCsvPathError(f"data file not found: {resolved.name}")
    if resolved.suffix.lower() not in ALLOWED_MANUAL_DATA_SUFFIXES:
        raise ManualCsvPathError(f"unsupported data file extension: {resolved.suffix}")
    if is_git_tracked(resolved, repo_root):
        raise ManualCsvPathError("refusing git-tracked data input path")
    return resolved


def resolve_manual_csv_path(csv_path: str, *, repo_root: Path) -> Path:
    resolved = Path(csv_path).expanduser().resolve()
    if not resolved.is_file():
        raise ManualCsvPathError(f"csv file not found: {resolved.name}")
    if is_git_tracked(resolved, repo_root):
        raise ManualCsvPathError("refusing git-tracked csv input path")
    return resolved
