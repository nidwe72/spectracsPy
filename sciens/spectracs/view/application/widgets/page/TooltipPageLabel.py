from PySide6.QtWidgets import QToolTip

from sciens.spectracs.view.application.widgets.page.PageLabel import PageLabel


class TooltipPageLabel(PageLabel):
    # A PageLabel (gray form-field chip) whose tooltip also pops on CLICK — the desktop affordance for the
    # metric descriptions (a phone has no hover). Hover still works too via setToolTip. SPEC §17 / §6.

    def mousePressEvent(self, event):
        tooltip = self.toolTip()
        if tooltip:
            QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
        super().mousePressEvent(event)
