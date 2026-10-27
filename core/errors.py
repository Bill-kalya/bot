class TradingError(Exception):
    """Base."""


class Halt(TradingError):
    """Enter HALTED state. No new entries until operator reset."""


class Reject(TradingError):
    """Risk engine refusal. Not fatal; logged and skipped."""


class ReconcileMismatch(Halt):
    """Local vs exchange state disagrees. Always halts."""