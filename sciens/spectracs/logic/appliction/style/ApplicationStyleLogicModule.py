from PySide6.QtGui import QColor

from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.appliction.style.Metrics import Metrics


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
        # Bootstrap 'secondary' — neutral gray, matching the PageLabel background
        # (surfaceAlt). Used for non-primary actions like a dialog's Cancel. #404040
        result=QColor.fromRgb(64, 64, 64)
        return result

    def getSecondaryPressedColor(self):
        # Slightly lighter gray for hover/pressed of secondary buttons. #4A4A4A
        result=QColor.fromRgb(74, 74, 74)
        return result

    def getSuccessColor(self):
        # Reuse primary green (fewer greens, per spec decision D4).
        return self.getPrimaryColor()

    def getInfoColor(self):
        # Bootstrap 'info' — light gray PLACEHOLDER for now (overrides spec D3 teal
        # until a real info hue is chosen). #8A8A8A
        result=QColor.fromRgb(138, 138, 138)
        return result

    def getInfoPressedColor(self):
        # Darker gray for hover/pressed of info buttons. #757575
        result=QColor.fromRgb(117, 117, 117)
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

    # ------------------------------------------------------------------ #
    # Global application stylesheet, generated from the getters above so
    # the QSS and painted widgets share one source of truth (spec P5).
    # ------------------------------------------------------------------ #

    APPLICATION_STYLE_SHEET_TEMPLATE = r'''
/*
	Copyright 2013 Emanuel Claesson

	Licensed under the Apache License, Version 2.0 (the "License");
	you may not use this file except in compliance with the License.
	You may obtain a copy of the License at

		http://www.apache.org/licenses/LICENSE-2.0

	Unless required by applicable law or agreed to in writing, software
	distributed under the License is distributed on an "AS IS" BASIS,
	WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
	See the License for the specific language governing permissions and
	limitations under the License.
*/

/*
	COLOR_DARK     = {background}
	COLOR_MEDIUM   = {surface}
	COLOR_MEDLIGHT = {border}
	COLOR_LIGHT    = {text}
	COLOR_ACCENT   = {primary}
*/

* {{
	background: {background};
	color: {text};
}}

/* Borders are opt-in, not universal (spec Workstream C / C1). Inputs and
   titled group boxes get them explicitly below; everything else is flat. */
QLineEdit {{
	border: 1px solid {border};
}}

QComboBox {{
	border: 1px solid {border};
}}

QFrame{{
    background: {background};
    border:none;
}}

/* E2: image/video preview targets get a faint outline so an empty feed reads
   as a defined "image area", not an invisible void (spec Workstream C / C2). */
BaseImageViewModule, BaseVideoViewModule {{
    border: 1px solid {border};
}}

QStackedWidget{{
    border: 1px solid {border};
}}

/*
QGroupBox{{
    border: 1px solid {border};
}}

QTabWidget{{
    border: none;
}}

QTab{{
    border: none;
}}

QLineEdit{{
    border: 1px solid {border};
}}

QComboBox{{
    border: 1px solid {border};
}}
*/

/*https://doc.qt.io/qt-5/stylesheet-examples.html#customizing-qtabwidget-and-qtabbar*/
QTabWidget::pane {{ /* The tab widget frame: a bordered card whose content is
    padded inside the border (spec C9). */
    border: 1px solid {border};
    padding: {panelPadding}px;
}}

/* The QStackedWidget that QTabWidget uses internally to host tab pages must NOT
   draw the generic stacked-widget border - else it doubles with the pane card
   and the content panels inside (spec C10). */
QTabWidget QStackedWidget {{
    border: none;
}}

QWidget::item:selected {{
	background: {primary};
}}

QCheckBox, QRadioButton {{
	border: none;
}}

QRadioButton::indicator, QCheckBox::indicator {{
	width: 13px;
	height: 13px;
}}

QRadioButton::indicator::unchecked, QCheckBox::indicator::unchecked {{
	border: 1px solid {border};
	background: none;
}}

QRadioButton::indicator:unchecked:hover, QCheckBox::indicator:unchecked:hover {{
	border: 1px solid {text};
}}

QRadioButton::indicator::checked, QCheckBox::indicator::checked {{
	border: 1px solid {border};
	background: {border};
}}

QRadioButton::indicator:checked:hover, QCheckBox::indicator:checked:hover {{
	border: 1px solid {text};
	background: {text};
}}

QGroupBox {{
	margin-top: 6px;
	border: 1px solid {border};
}}

/* Untitled holders (nav rows, region wrappers) tagged plain=True in view code:
   no border, no reserved title gap (spec Workstream C / C2). */
QGroupBox[plain="true"] {{
	border: none;
	margin-top: 0px;
}}

/* Demoted single-child frames keep their title as a lightweight section
   label: no border, but retain the base top margin so the title isn't
   clipped (spec Workstream C / C2b). */
QGroupBox[sectionLabel="true"] {{
	border: none;
}}

/* The section-label heading aligns with its field's left edge, not the
   bordered-panel title inset (spec C11). */
QGroupBox[sectionLabel="true"]::title {{
	left: 0px;
}}


QGroupBox::title {{
	top: -7px;
	left: 7px;	
}}

/* E1: the top-level page container is never bordered - the breadcrumb title
   becomes a plain header strip, and inner groups stop being double-framed
   (spec Workstream C / C3). */
QGroupBox#PageWidget_topMost {{
	border: none;
}}

QGroupBox#PageWidget_topMost::title {{
	color: {primary};
}}

QScrollBar {{
	border: 1px solid {border};
	background: {background};
}}

QScrollBar:horizontal {{
	height: 15px;
	margin: 0px 0px 0px 32px;
}}

QScrollBar:vertical {{
	width: 15px;
	margin: 32px 0px 0px 0px;
}}

QScrollBar::handle {{
	background: {surface};
	border: 1px solid {border};
}}

QScrollBar::handle:horizontal {{
	border-width: 0px 1px 0px 1px;
}}

QScrollBar::handle:vertical {{
	border-width: 1px 0px 1px 0px;
}}

QScrollBar::handle:horizontal {{
	min-width: 20px;
}}

QScrollBar::handle:vertical {{
	min-height: 20px;
}}

QScrollBar::add-line, QScrollBar::sub-line {{
	background:{surface};
	border: 1px solid {border};
	subcontrol-origin: margin;
}}

QScrollBar::add-line {{
	position: absolute;
}}

QScrollBar::add-line:horizontal {{
	width: 15px;
	subcontrol-position: left;
	left: 15px;
}}

QScrollBar::add-line:vertical {{
	height: 15px;
	subcontrol-position: top;
	top: 15px;
}}

QScrollBar::sub-line:horizontal {{
	width: 15px;
	subcontrol-position: top left;
}}

QScrollBar::sub-line:vertical {{
	height: 15px;
	subcontrol-position: top;
}}

QScrollBar:left-arrow, QScrollBar::right-arrow, QScrollBar::up-arrow, QScrollBar::down-arrow {{
	border: 1px solid {border};
	width: 3px;
	height: 3px;
}}

QScrollBar::add-page, QScrollBar::sub-page {{
	background: none;
}}

QAbstractButton {{
    height:50px;
	background-color:  {primary};
	font:bold;
	/* Explicit border so a default/focused button (e.g. the login dialog's "Login")
	   doesn't fall back to the native blue default-frame. */
	border: none;
}}

/* Keep the default/focused button flat too (no native highlight frame). */
QPushButton:default, QPushButton:focus {{
	border: none;
	outline: none;
}}

/* Semantic button variants (Bootstrap-style roles, spec P7). Tag a button in view
   code with setProperty("buttonType", "info"|"secondary"|"danger") to recolour it;
   default (no property) stays the primary green. */
QAbstractButton[buttonType="info"] {{
	background-color: {info};
}}
QAbstractButton[buttonType="info"]:hover, QAbstractButton[buttonType="info"]:pressed {{
	background-color: {infoPressed};
}}
QAbstractButton[buttonType="secondary"] {{
	background-color: {secondary};
}}
QAbstractButton[buttonType="secondary"]:hover, QAbstractButton[buttonType="secondary"]:pressed {{
	background-color: {secondaryPressed};
}}
QAbstractButton[buttonType="danger"] {{
	background-color: {danger};
}}

QAbstractButton:disabled {{
	background-color:  {disabled};
}}

QAbstractButton:hover {{
	background:  {primaryPressed};
}}

QAbstractButton:pressed {{
	background:  {primaryPressed};
}}

/* QCheckBox/QRadioButton ARE QAbstractButtons, so the green button fill (incl. its
   :hover/:pressed) above applies to them too — making a bare checkbox look like a big
   green box around a tiny indicator. Flatten the widget background back to transparent
   (only the ::indicator, styled above, should show). MUST come after the QAbstractButton
   rules (later rule wins). Height is left to callers (a custom ToggleSwitch wants its own
   size); form checkboxes set a compact fixed height in code. */
QCheckBox, QRadioButton,
QCheckBox:hover, QCheckBox:pressed,
QRadioButton:hover, QRadioButton:pressed {{
	background: transparent;
}}

QAbstractItemView {{
	show-decoration-selected: 1;
	selection-background-color: gray;
	selection-color: {text};
	alternate-background-color: {surface};
}}

QHeaderView {{
	border: none;
}}

QHeaderView::section {{
	background: {surfaceAlt};
	/* Only a right+bottom separator (single 1px line) so header dividers land exactly on the
	   body gridlines; the outer frame is drawn by QTableView's border. */
	border: none;
	border-right: 1px solid {border};
	border-bottom: 1px solid {border};
	padding: 4px;
	font-weight: bold;
}}

QHeaderView::section:selected, QHeaderView::section::checked {{
	background: {surface};
}}

QTableView {{
	gridline-color: {border};
	border: 1px solid {border};
}}

QTabBar {{
	margin-left: 2px;
}}

QTabBar::tab {{
	border-radius: 0px;
	padding: 4px;
	margin: 4px;	
	background: {surface};
}}

QTabBar::tab:selected {{
	background: {primary};

}}

QComboBox::down-arrow {{
	border: 1px solid {border};
	background: {surface};
}}

QComboBox::drop-down {{
	border: 1px solid {border};
	background: {surface};
}}

QComboBox::down-arrow {{
	width: 3px;
	height: 3px;
	border: 1px solid {border};
}}

QAbstractSpinBox {{
	padding-right: 15px;
	border: 1px solid {border};
}}

QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
	border: 1px solid {border};
	background: {surface};
	subcontrol-origin: border;
}}

QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {{
	width: 3px;
	height: 3px;
	border: 1px solid {border};
}}

QSlider {{
	border: none;
}}

QSlider::groove:horizontal {{
	height: 5px;
	margin: 4px 0px 4px 0px;
}}

QSlider::groove:vertical {{
	width: 5px;
	margin: 0px 4px 0px 4px;
}}

QSlider::handle {{
	border: 1px solid {border};
	background: {surface};
}}

QSlider::handle:horizontal {{
	width: 15px;
	margin: -4px 0px -4px 0px;
}}

QSlider::handle:vertical {{
	height: 15px;
	margin: 0px -4px 0px -4px;
}}

QSlider::add-page:vertical, QSlider::sub-page:horizontal {{
	background: {primary};
}}

QSlider::sub-page:vertical, QSlider::add-page:horizontal {{
	background: {surface};
}}

QLabel {{	
	border: none;;
	background: #00000000;	
}}

QProgressBar {{
	text-align: center;
}}

QProgressBar::chunk {{
	width: 1px;
	background-color: {primary};
}}

QMenu::separator {{
	background: {surface};
}}


PageLabel {{
	border: none;	
	background: {surfaceAlt};
	padding-left:10px;
}}

PageWidget{{
    border: 1px solid #00000000;
    background:#00000000;
}}

QLineEdit[readOnly="true"]{{
    border: 1px solid gray;
    color:gray;
}}


QLabel[style-primary="true"]{{
    color:{primary};
}}

QLabel[style-bold="true"]{{
    font-weight:bold;
    font-size:20px;
}}

QLabel[style-large="true"]{{
    font-size:20px;
}}


'''

    def getApplicationStyleSheet(self):
        return self.APPLICATION_STYLE_SHEET_TEMPLATE.format(
            background=self.getBackgroundColor().name(),
            text=self.getTextColor().name(),
            border=self.getBorderColor().name(),
            primary=self.getPrimaryColor().name(),
            primaryPressed=self.getPrimaryPressedColor().name(),
            surface=self.getSurfaceColor().name(),
            disabled=self.getPrimaryColorDisabled().name(),
            surfaceAlt=self.getSurfaceAltColor().name(),
            info=self.getInfoColor().name(),
            infoPressed=self.getInfoPressedColor().name(),
            secondary=self.getSecondaryColor().name(),
            secondaryPressed=self.getSecondaryPressedColor().name(),
            danger=self.getDangerColor().name(),
            panelPadding=Metrics.M,
        )

