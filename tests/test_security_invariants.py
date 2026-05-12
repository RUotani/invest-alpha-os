"""Static checks for safe-push staging safety (Hotfix B invariants)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE_PUSH = ROOT / "scripts" / "safe_commit_push.sh"


def test_safe_push_script_has_no_git_add_dash_a() -> None:
    text = SAFE_PUSH.read_text(encoding="utf-8")
    assert "git add -A" not in text
    assert "add --dry-run -A" not in text


def test_safe_push_conflict_abort_message() -> None:
    text = SAFE_PUSH.read_text(encoding="utf-8")
    assert "conflict detected; resolve before safe-push" in text
    # Conflict XY tokens (subset).
    for xy in ("UU", "AA", "DD", "AU", "UA", "DU", "UD", "TT"):
        assert xy in text


def test_safe_push_pre_staged_abort_message() -> None:
    text = SAFE_PUSH.read_text(encoding="utf-8")
    assert "pre-staged changes detected. Unstage them first:" in text
    assert "git restore --staged <path>" in text
    assert "git restore --staged ." in text


def test_safe_push_uses_git_add_double_dash() -> None:
    text = SAFE_PUSH.read_text(encoding="utf-8")
    assert 'git -C "${ROOT}" add -- "${STAGE_PATHS[@]}"' in text


def test_safe_push_forbidden_path_guards_retained() -> None:
    text = SAFE_PUSH.read_text(encoding="utf-8")
    for fragment in (
        '[[ "${base}" == ".env" ]]',
        ".env.example",
        "credentials.json",
        "token.json",
        "(^|/)secrets/",
        "(^|/)keys/",
        "^outputs/",
        ".ai/reviews/",
    ):
        assert fragment in text


def test_safe_push_rename_abort_documented_in_script() -> None:
    text = SAFE_PUSH.read_text(encoding="utf-8")
    assert "rename or copy detected" in text
    assert "git mv / separate commit" in text or "git mv" in text
