from sciens.base.Singleton import Singleton


class Metrics(Singleton):
    """Single source of truth for layout spacing.

    One scale, referenced everywhere instead of raw pixel numbers. See
    docs/SPEC_visual_harmonization.md (workstream A).

    Application contract:
        - page-level container margin -> M
        - spacing between sibling widgets -> S
        - inner padding of a bordered/card panel -> S
    """

    XS = 4
    S = 8
    M = 12
    L = 16
    XL = 24
