import ast
from pathlib import Path

RISK_DIR = Path(__file__).resolve().parent.parent / "risk"
FORBIDDEN = {"exchange", "ccxt", "storage", "sqlite3"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                out.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module.split(".")[0])
    return out


def test_risk_engine_has_no_io_imports() -> None:
    offenders = {}
    for path in RISK_DIR.rglob("*.py"):
        found = _imports(path) & FORBIDDEN
        if found:
            offenders[str(path)] = found
    assert not offenders, f"risk/ must be pure: {offenders}"