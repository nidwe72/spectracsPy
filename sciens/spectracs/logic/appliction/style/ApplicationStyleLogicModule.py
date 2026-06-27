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
	border: 1px solid {border};
}}

QFrame{{
    background: {background};
    border:none;
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
QTabWidget::pane {{ /* The tab widget frame */
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
}}


QGroupBox::title {{
	top: -7px;
	left: 7px;	
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

QAbstractItemView {{
	show-decoration-selected: 1;
	selection-background-color: gray;
	selection-color: {text};
	alternate-background-color: {surface};
}}

QHeaderView {{
	border: 1px solid {border};
}}

QHeaderView::section {{
	background: {background};
	border: 1px solid {border};
	padding: 4px;
}}

QHeaderView::section:selected, QHeaderView::section::checked {{
	background: {surface};
}}

QTableView {{
	gridline-color: {border};
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
        )

