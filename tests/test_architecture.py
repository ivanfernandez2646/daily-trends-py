import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "daily_trends_py"
TESTS = ROOT / "tests"
APP = SOURCE / "apps" / "cms_backend"
APP_TESTS = TESTS / "apps" / "cms_backend"

# Built from parts so this file does not match itself.
APP_STATE = re.compile(r"\bapp\." + "state" + r"\b")
DISHKA_IMPORT = re.compile(r"^\s*(from|import)\s+dishka\b", re.MULTILINE)


def _python_files(*roots: Path) -> list[Path]:
    return [path for root in roots for path in root.rglob("*.py")]


def test_no_code_reads_or_writes_the_untyped_app_state() -> None:
    offenders = [
        path.relative_to(ROOT)
        for path in _python_files(SOURCE, TESTS)
        if APP_STATE.search(path.read_text())
    ]

    assert offenders == []


def test_only_the_app_knows_the_dependency_injection_container() -> None:
    offenders = [
        path.relative_to(ROOT)
        for path in _python_files(SOURCE, TESTS)
        if DISHKA_IMPORT.search(path.read_text())
        and not path.is_relative_to(APP)
        and not path.is_relative_to(APP_TESTS)
    ]

    assert offenders == []
