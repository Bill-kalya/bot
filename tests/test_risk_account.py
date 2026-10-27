from risk.account import Account


def test_daily_loss_pct_zero_when_at_baseline() -> None:
    a = Account(equity=10.0, daily_baseline=10.0, peak_equity=10.0, open_positions=0)
    assert a.daily_loss_pct == 0.0


def test_daily_loss_pct_positive_after_loss() -> None:
    a = Account(equity=8.0, daily_baseline=10.0, peak_equity=10.0, open_positions=0)
    assert abs(a.daily_loss_pct - 0.20) < 1e-9


def test_drawdown_uses_peak() -> None:
    a = Account(equity=7.0, daily_baseline=10.0, peak_equity=10.0, open_positions=0)
    assert abs(a.drawdown_pct - 0.30) < 1e-9