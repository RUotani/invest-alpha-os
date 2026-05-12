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


# --- Hotfix C (ops scripts: no shell sourcing of .env) -------------------------

_OPS = [
    ROOT / "scripts" / "env_doctor.sh",
    ROOT / "scripts" / "jquants_smoke.sh",
    ROOT / "scripts" / "daily_check.sh",
]


def test_ops_scripts_do_not_shell_source_dotenv() -> None:
    for path in _OPS:
        text = path.read_text(encoding="utf-8")
        assert 'source "${ROOT}/.env"' not in text
        assert "source .env" not in text


def test_load_jquants_env_script_avoids_exec_hooks() -> None:
    text = (ROOT / "scripts" / "load_jquants_env.py").read_text(encoding="utf-8")
    assert "os.system" not in text
    assert "subprocess." in text  # run mode
    assert "eval(" not in text
