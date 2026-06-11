from __future__ import annotations


class RendererError(ValueError):
    pass


class UnknownStyleError(RendererError):
    pass


class UnknownLexerError(RendererError):
    pass


class UnknownBackgroundError(RendererError):
    pass


class InvalidLogoPlacementError(RendererError):
    pass


class InvalidRendererOptionError(RendererError):
    pass


class UnsupportedImageError(RendererError):
    pass
