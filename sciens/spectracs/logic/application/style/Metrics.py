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

    # Vertical breathing room under the breadcrumb/page title before the first row (R2, issue 5).
    SPACE_AFTER_BREADCRUMB = L

    # G5: reasonable max width for a short form / dialog content column. Capping + centring at this width
    # keeps a maximized desktop window readable; on phone-mode / Android the window is narrower so it never
    # binds (full width). Referenced by PageWidget.maxContentWidth (opt-in). Currently used by Login.
    CONTENT_MAX_WIDTH = 560

    @staticmethod
    def applyPanelPadding(layout):
        """Uniform inner padding (P=M) for a bordered panel's content, so panel
        content never hugs the frame and every panel matches (spec C6)."""
        layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
