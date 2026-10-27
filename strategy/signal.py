"""Strategy signal helpers. Re-exports Signal so strategy modules only import
from here and never from core directly (keeps the boundary clean)."""
from core.types import Signal  # noqa: F401