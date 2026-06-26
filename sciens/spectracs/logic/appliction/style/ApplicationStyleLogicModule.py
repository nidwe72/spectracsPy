from PySide6.QtGui import QColor

from sciens.base.Singleton import Singleton


class ApplicationStyleLogicModule(Singleton):

    # ------------------------------------------------------------------ #
    # Brand / semantic palette (Bootstrap-style roles).
    # See docs/SPEC_visual_harmonization.md (workstream B).
    # ------------------------------------------------------------------ #

    def getPrimaryColor(self):
        # Brand green / primary action / active-selected. #3D7848
        result=QColor.fromRgb(61, 120, 72)
        return result

    def getPrimaryPressedColor(self):
        # Darker green for hover/pressed of primary. #33663d
        result=QColor.fromRgb(51, 102, 61)
        return result

    def getPrimaryTextColor(self):
        result=QColor.fromRgb(255, 255, 255)
        return result

    def getPrimaryColorDisabled(self):
        result=QColor.fromRgb(80, 98, 84)
        return result
        # #506254

    def getSecondaryColor(self):
        # Neutral / info-like buttons. Same gray as the border ramp. #5A5A5A
        result=QColor.fromRgb(90, 90, 90)
        return result

    def getSuccessColor(self):
        # Reuse primary green (fewer greens, per spec decision D4).
        return self.getPrimaryColor()

    def getInfoColor(self):
        # Muted teal — stays in the green family, NOT blue. #3D7878
        result=QColor.fromRgb(61, 120, 120)
        return result

    def getWarningColor(self):
        # Muted amber. #C9942E
        result=QColor.fromRgb(201, 148, 46)
        return result

    def getDangerColor(self):
        # Muted red. #B0544E
        result=QColor.fromRgb(176, 84, 78)
        return result

    # ------------------------------------------------------------------ #
    # Neutral ramp — names the grays already used across the QSS.
    # ------------------------------------------------------------------ #

    def getBackgroundColor(self):
        # Main window / page background. #191919
        result=QColor.fromRgb(25, 25, 25)
        return result

    def getSurfaceColor(self):
        # Controls / panels / scrollbars. #353535
        result=QColor.fromRgb(53, 53, 53)
        return result

    def getSurfaceAltColor(self):
        # Slightly lighter surface (e.g. PageLabel). #404040
        result=QColor.fromRgb(64, 64, 64)
        return result

    def getBorderColor(self):
        # Borders / unchecked indicators. #5A5A5A
        result=QColor.fromRgb(90, 90, 90)
        return result

    def getTextColor(self):
        # Default body text. #DDDDDD
        result=QColor.fromRgb(221, 221, 221)
        return result

    def getSecondaryChartGridColor(self):
        result=QColor.fromRgb(30, 30, 30)
        return result
