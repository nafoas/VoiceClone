"""Prince's voice for the Little Self project."""

from .params import Params, StyleMod

__all__ = ["Params", "StyleMod", "PrinceVoice"]


def __getattr__(name):
    if name == "PrinceVoice":  # lazy: avoids loading torch for params-only use
        from .engine import PrinceVoice
        return PrinceVoice
    raise AttributeError(name)
