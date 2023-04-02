import sys

from PySide6 import QtWidgets
from PySide6.QtGui import QGuiApplication

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from view.main.MainContainerViewModule import MainContainerViewModule

app = QtWidgets.QApplication(sys.argv)

#todo:extract
app.setStyleSheet("""
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
	COLOR_DARK     = #191919
	COLOR_MEDIUM   = #353535
	COLOR_MEDLIGHT = #5A5A5A
	COLOR_LIGHT    = #DDDDDD
	COLOR_ACCENT   = #3D7848
*/

* {
	background: #191919;
	color: #DDDDDD;
	border: 1px solid #5A5A5A;
}

QFrame{
    background: #191919;
    border:none;
}

QStackedWidget{
    border: 1px solid #5A5A5A;
}

/*
QGroupBox{
    border: 1px solid #5A5A5A;
}

QTabWidget{
    border: none;
}

QTab{
    border: none;
}

QLineEdit{
    border: 1px solid #5A5A5A;
}

QComboBox{
    border: 1px solid #5A5A5A;
}
*/

/*https://doc.qt.io/qt-5/stylesheet-examples.html#customizing-qtabwidget-and-qtabbar*/
QTabWidget::pane { /* The tab widget frame */
    border: none;
}

QWidget::item:selected {
	background: #3D7848;
}

QCheckBox, QRadioButton {
	border: none;
}

QRadioButton::indicator, QCheckBox::indicator {
	width: 13px;
	height: 13px;
}

QRadioButton::indicator::unchecked, QCheckBox::indicator::unchecked {
	border: 1px solid #5A5A5A;
	background: none;
}

QRadioButton::indicator:unchecked:hover, QCheckBox::indicator:unchecked:hover {
	border: 1px solid #DDDDDD;
}

QRadioButton::indicator::checked, QCheckBox::indicator::checked {
	border: 1px solid #5A5A5A;
	background: #5A5A5A;
}

QRadioButton::indicator:checked:hover, QCheckBox::indicator:checked:hover {
	border: 1px solid #DDDDDD;
	background: #DDDDDD;
}

QGroupBox {
	margin-top: 6px;
}


QGroupBox::title {
	top: -7px;
	left: 7px;	
}

QGroupBox#PageWidget_topMost::title {	
	color: #3D7848;	
}

QScrollBar {
	border: 1px solid #5A5A5A;
	background: #191919;
}

QScrollBar:horizontal {
	height: 15px;
	margin: 0px 0px 0px 32px;
}

QScrollBar:vertical {
	width: 15px;
	margin: 32px 0px 0px 0px;
}

QScrollBar::handle {
	background: #353535;
	border: 1px solid #5A5A5A;
}

QScrollBar::handle:horizontal {
	border-width: 0px 1px 0px 1px;
}

QScrollBar::handle:vertical {
	border-width: 1px 0px 1px 0px;
}

QScrollBar::handle:horizontal {
	min-width: 20px;
}

QScrollBar::handle:vertical {
	min-height: 20px;
}

QScrollBar::add-line, QScrollBar::sub-line {
	background:#353535;
	border: 1px solid #5A5A5A;
	subcontrol-origin: margin;
}

QScrollBar::add-line {
	position: absolute;
}

QScrollBar::add-line:horizontal {
	width: 15px;
	subcontrol-position: left;
	left: 15px;
}

QScrollBar::add-line:vertical {
	height: 15px;
	subcontrol-position: top;
	top: 15px;
}

QScrollBar::sub-line:horizontal {
	width: 15px;
	subcontrol-position: top left;
}

QScrollBar::sub-line:vertical {
	height: 15px;
	subcontrol-position: top;
}

QScrollBar:left-arrow, QScrollBar::right-arrow, QScrollBar::up-arrow, QScrollBar::down-arrow {
	border: 1px solid #5A5A5A;
	width: 3px;
	height: 3px;
}

QScrollBar::add-page, QScrollBar::sub-page {
	background: none;
}

QAbstractButton {
    height:50px;
	background-color:  #33663d;
	font:bold;
}

QAbstractButton:disabled {
	background-color:  #506254;
}

QAbstractButton:hover {
	background:  #3d7848;
}

QAbstractButton:pressed {
	background:  #3d7848;	
}

QAbstractItemView {
	show-decoration-selected: 1;
	selection-background-color: gray;
	selection-color: #DDDDDD;
	alternate-background-color: #353535;
}

QHeaderView {
	border: 1px solid #5A5A5A;
}

QHeaderView::section {
	background: #191919;
	border: 1px solid #5A5A5A;
	padding: 4px;
}

QHeaderView::section:selected, QHeaderView::section::checked {
	background: #353535;
}

QTableView {
	gridline-color: #5A5A5A;
}

QTabBar {
	margin-left: 2px;
}

QTabBar::tab {
	border-radius: 0px;
	padding: 4px;
	margin: 4px;	
	background: #353535;
}

QTabBar::tab:selected {
	background: #33663d;
	
}

QComboBox::down-arrow {
	border: 1px solid #5A5A5A;
	background: #353535;
}

QComboBox::drop-down {
	border: 1px solid #5A5A5A;
	background: #353535;
}

QComboBox::down-arrow {
	width: 3px;
	height: 3px;
	border: 1px solid #5A5A5A;
}

QAbstractSpinBox {
	padding-right: 15px;
}

QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
	border: 1px solid #5A5A5A;
	background: #353535;
	subcontrol-origin: border;
}

QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {
	width: 3px;
	height: 3px;
	border: 1px solid #5A5A5A;
}

QSlider {
	border: none;
}

QSlider::groove:horizontal {
	height: 5px;
	margin: 4px 0px 4px 0px;
}

QSlider::groove:vertical {
	width: 5px;
	margin: 0px 4px 0px 4px;
}

QSlider::handle {
	border: 1px solid #5A5A5A;
	background: #353535;
}

QSlider::handle:horizontal {
	width: 15px;
	margin: -4px 0px -4px 0px;
}

QSlider::handle:vertical {
	height: 15px;
	margin: 0px -4px 0px -4px;
}

QSlider::add-page:vertical, QSlider::sub-page:horizontal {
	background: #3D7848;
}

QSlider::sub-page:vertical, QSlider::add-page:horizontal {
	background: #353535;
}

QLabel {	
	border: none;;
	background: #00000000;	
}

QProgressBar {
	text-align: center;
}

QProgressBar::chunk {
	width: 1px;
	background-color: #3D7848;
}

QMenu::separator {
	background: #353535;
}


PageLabel {
	border: none;	
	background: #404040;
	padding-left:10px;
}

PageWidget{
    border: 1px solid #00000000;
    background:#00000000;
}

QLineEdit[readOnly="true"]{
    border: 1px solid gray;
    color:gray;
}


QLabel[style-primary="true"]{
    color:#3D7848;
}

QLabel[style-bold="true"]{
    font-weight:bold;
    font-size:20px;
}

QLabel[style-large="true"]{
    font-size:20px;
}


""")

mainContainerViewModule = MainContainerViewModule()
geometry = QGuiApplication.primaryScreen().availableGeometry()
mainContainerViewModule.setMinimumWidth(geometry.width()/2)
mainContainerViewModule.setMinimumHeight(geometry.height()*0.9)
mainContainerViewModule.setWindowTitle("Spectracs")

ApplicationContextLogicModule().getNavigationHandler().mainContainerViewModule = mainContainerViewModule
mainContainerViewModule.show()

try:
    import pyi_splash

    pyi_splash.update_text('UI Loaded ...')
    pyi_splash.close()
except:
    pass

sys.exit(app.exec())




