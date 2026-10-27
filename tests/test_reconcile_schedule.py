from execution.reconcile import should_reconcile


class _Cfg:
    reconcile_every_loops = 10


def test_should_not_reconcile_at_zero():
    assert should_reconcile(0, _Cfg()) is False


def test_should_reconcile_on_boundary():
    assert should_reconcile(10, _Cfg()) is True
    assert should_reconcile(20, _Cfg()) is True


def test_should_not_reconcile_off_boundary():
    assert should_reconcile(7, _Cfg()) is False


def test_zero_disables_reconcile():
    class C:
        reconcile_every_loops = 0
    assert should_reconcile(100, C()) is False