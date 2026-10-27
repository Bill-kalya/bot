import ast
from pathlib import Path

PAPER = Path(__file__).resolve().parent.parent / "execution" / "paper.py"
FORBIDDEN_CALLS = {"create_order", "create_market_order", "create_stop_market",
                   "set_leverage", "cancel_order"}


def test_paper_module_has_no_trading_calls():
    tree = ast.parse(PAPER.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in FORBIDDEN_CALLS, \
                f"paper.py must never call {node.func.attr}"