from PySide6 import QtGui
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget, QGridLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel, QStyleOption, \
    QFrame, QScrollArea, QSizePolicy

from PySide6.QtCore import Qt

from sciens.base.PlatformUtil import is_android
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.view.application.widgets.page.PageLabel import PageLabel

class PageWidget(QFrame):
    mainContainerWidgets = None
    verticalLayout:bool=True
    # Single-content pages (one field) set this so their titled container is
    # demoted to a borderless section label, not a frame (spec C2b / E5).
    borderlessMainContainer:bool=False
    # Form/editor pages set this so their fields pack at the TOP (natural height)
    # instead of spreading over the panel height. Hub/menu pages leave it False so
    # their large controls fill the height intentionally (see docs/DESIGN_GUIDE.md).
    compactMainContainer:bool=False
    # Opt-in (with compactMainContainer): centre the content block vertically instead of top-packing it —
    # for short forms like Login. Adds a leading spacer to match the trailing one.
    verticalCenterMainContainer:bool=False
    # G5 opt-in: cap the content column at Metrics.CONTENT_MAX_WIDTH and centre it horizontally (short forms
    # like Login on a wide desktop window). The nav footer stays full-width. Phone width < cap → no effect.
    maxContentWidth:bool=False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self):

        layout=QGridLayout()
        layout.setSpacing(Metrics.S)
        self.setLayout(layout)


        if self._isTopMostPageWidget():
            # Page-level container: the one place that gets an outer margin.
            layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        else:
            # Nested page widgets stay flush so margins don't compound.
            layout.setContentsMargins(0,0,0,0)
            self.setContentsMargins(0,0,0,0)

        mainContainer = self.createMainContainer()

        # G5: cap + centre the content column (opt-in, top-most only). The container expands up to the cap
        # and is centred by side spacers; the nav footer below stays full-width. Phone width < cap → fills.
        content = mainContainer
        if self.maxContentWidth and self._isTopMostPageWidget():
            mainContainer.setMaximumWidth(Metrics.CONTENT_MAX_WIDTH)
            mainContainer.setSizePolicy(QSizePolicy.Policy.Expanding, mainContainer.sizePolicy().verticalPolicy())
            content = QWidget()
            centreLayout = QHBoxLayout(content)
            centreLayout.setContentsMargins(0, 0, 0, 0)
            centreLayout.addStretch(1)
            centreLayout.addWidget(mainContainer)
            centreLayout.addStretch(1)

        if is_android() and self._isTopMostPageWidget():
            # On phones, tall forms must scroll rather than clip / get squeezed. Wrap only the
            # top-most page's content (never nested pages -> no nested scroll areas). Desktop is
            # untouched. Horizontal scroll off so content reflows to the screen width.
            scrollArea = QScrollArea()
            scrollArea.setWidgetResizable(True)
            scrollArea.setFrameShape(QFrame.Shape.NoFrame)
            scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scrollArea.setWidget(content)
            layout.addWidget(scrollArea, 0, 0, 1, 1)
        else:
            layout.addWidget(content, 0, 0, 1, 1)
        layout.setRowStretch(0,90)

        if self._isTopMostPageWidget():
            navigationGroupBox = self.createNavigationGroupBox()
            layout.addWidget(navigationGroupBox,1,0,1,1)


    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)  # borderless holder (spec C2)

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)  # align nav buttons to content edge (spec C7)
        result.setLayout(layout);

        return result

    def createMainContainer(self):
        title=self._getPageTitle()
        result=QGroupBox(title)

        borderless=False
        isTopMost=self._isTopMostPageWidget()
        if isTopMost:
            result.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            result.setObjectName('PageWidget_topMost')
            borderless=True
        elif self.borderlessMainContainer:
            result.setProperty("sectionLabel", True)
            borderless=True
        elif title == "":
            # Untitled nested container: nothing to label, so no frame - else it
            # double-borders with the surrounding widgets (spec C8).
            result.setProperty("plain", True)
            borderless=True

        #result.setFlat(True)

        layout=QGridLayout()
        if borderless:
            # Borderless container: no frame to protect, so NO horizontal indent
            # - otherwise nested peers stair-step out of alignment. Vertical only.
            # R2: the top-most page adds breathing room under the breadcrumb title (issue 5).
            topMargin = Metrics.SPACE_AFTER_BREADCRUMB if isTopMost else Metrics.S
            layout.setContentsMargins(0, topMargin, 0, Metrics.S)
        else:
            # Bordered panel: uniform inner padding (P=M) so content does not
            # hug the frame and matches every other panel (spec C6).
            layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        layout.setSpacing(Metrics.S)
        result.setLayout(layout)
        row=0
        # Vertical-centre pages (verticalCenterMainContainer) add a LEADING spacer too, so a short form
        # (e.g. Login) sits mid-height instead of top-packed. Compact-only + vertical.
        centerVertically = self.verticalCenterMainContainer and self.compactMainContainer and self.verticalLayout
        if centerVertically:
            layout.setRowStretch(0, 1)
            row = 1
        mainContainerWidgets = self.getMainContainerWidgets()
        for mainContainerWidgetName,mainContainerWidget in mainContainerWidgets.items():
            if self.verticalLayout:
                layout.addWidget(mainContainerWidget,row,0,1,1)
            else:
                layout.addWidget(mainContainerWidget, 0, row, 1, 1)
            row=row+1

        if self.compactMainContainer and self.verticalLayout:
            # Trailing spacer row absorbs the slack; with a leading spacer too the content centres,
            # otherwise it top-packs at natural height instead of spreading over the panel.
            layout.setRowStretch(row, 1)

        return result

    def _getPageTitle(self):
        return '';

    def getMainContainerWidgets(self):
        if self.mainContainerWidgets is None:
            self.mainContainerWidgets={}
        return self.mainContainerWidgets

    def createLabeledComponent(self,label:str,component:QWidget):
        container=QWidget()

        layout=QGridLayout()
        # No own margins: the field aligns to its container's content edge, so
        # peers at different nesting depths line up (spec C7).
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Metrics.S)
        container.setLayout(layout)
        labelComponent=PageLabel(label)
        # R1: the label fills its whole column so every field-label "chip" has the same width and
        # left/right edge — otherwise chips size to their text and read as ragged (issues 1,2).
        labelComponent.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(labelComponent,0,0,1,1)
        layout.setColumnStretch(0,30)

        layout.addWidget(component, 0, 1, 1, 1)
        layout.setColumnStretch(1, 70)

        return container

    def createForm(self, rows):
        """R1/B5: lay several (label, widget) rows in ONE shared grid so the label column is a single
        width across all rows — even rows that would otherwise live in separate createLabeledComponent
        containers and not share an edge. `rows` is a list of (labelText, component)."""
        container = QWidget()
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Metrics.S)
        container.setLayout(layout)
        for row, (labelText, component) in enumerate(rows):
            label = PageLabel(labelText)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            layout.addWidget(label, row, 0, 1, 1)
            layout.addWidget(component, row, 1, 1, 1)
        layout.setColumnStretch(0, 30)
        layout.setColumnStretch(1, 70)
        return container

    def createMessageLabel(self, text: str):
        """Rwrap: a prose/status label that wraps instead of overflowing (and being clipped both
        sides, as the connection message was). Use for any multi-word informational text."""
        result = QLabel(text)
        result.setWordWrap(True)
        return result

    def createSection(self, title: str, content: QWidget):
        """R7: one section pattern app-wide — a borderless titled heading (sectionLabel) over its
        content, so sections stop mixing bordered group-boxes and bare labels."""
        result = QGroupBox(title)
        result.setProperty("sectionLabel", True)  # borderless heading (spec C2b)
        layout = QGridLayout()
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        layout.setSpacing(Metrics.S)
        result.setLayout(layout)
        layout.addWidget(content, 0, 0, 1, 1)
        return result

    def _isTopMostPageWidget(self):
        parent=self.parent()
        result=not isinstance(parent,PageWidget)
        return result

    def setStylesheetOnlySelf(self, stylesheet: str) -> None:
        objectName = self.objectName() if self.objectName() != "" else str(id(self))
        self.setObjectName(objectName)
        self.setStyleSheet("#%s {%s}" % (objectName, stylesheet))



