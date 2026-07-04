import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QPushButton, QFileDialog, QGroupBox, QGridLayout, QWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.general.ToggleSwitch import ToggleSwitch
from sciens.spectracs.view.application.widgets.image.BaseImageViewModule import BaseImageViewModule
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.logic.appliction.style.Metrics import Metrics

class VirtualSpectrometerViewModule(PageWidget):

    __doSavePhysicallyCapturedImagesComponent:ToggleSwitch=None
    openPictureButton:QPushButton=None
    __imageViewModule:BaseImageViewModule=None
    __doSavePhysicallyCapturedImagesComponent:ToggleSwitch=None

    def createMainContainer(self):
        result=super().createMainContainer()
        result.setTitle("Settings > Virtual spectrometer")
        return result

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        imageViewModule = self.__getImageViewModule()
        result['imageViewModule'] = imageViewModule

        result['doSavePhysicallyCapturedImagesComponent']=self.createLabeledComponent('save physically captured images', self.__getDoSavePhysicallyCapturedImagesComponent())

        buttonsPanel = self.__createButtonsPanel()
        result[buttonsPanel.objectName()] = buttonsPanel

        return result

    def __getDoSavePhysicallyCapturedImagesComponent(self):
        if self.__doSavePhysicallyCapturedImagesComponent is None:
            self.__doSavePhysicallyCapturedImagesComponent=ToggleSwitch(None, Qt.gray, ApplicationStyleLogicModule().getPrimaryColor())
            self.__doSavePhysicallyCapturedImagesComponent.stateChanged.connect(self.onStateChangedDoSavePhysicallyCapturedImagesComponent)

        return self.__doSavePhysicallyCapturedImagesComponent

    def __createButtonsPanel(self):
        buttonsPanel = QWidget()
        buttonsPanel.setObjectName(
            'VirtualSpectrometerViewModule.buttonsPanel')

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # holder adds no indent (spec C8)
        buttonsPanel.setLayout(layout)

        self.openPictureButton=QPushButton('Set image folder…')
        self.openPictureButton.clicked.connect(self.onClickedOpenPictureButton)
        layout.addWidget(self.openPictureButton, 0, 0, 1, 1)

        return buttonsPanel

    def __getImageViewModule(self):
        if self.__imageViewModule is None:
            self.__imageViewModule=BaseImageViewModule()
            self.__imageViewModule.initialize()
        return self.__imageViewModule

    def _getPageTitle(self):
        return "Virtual spectrometer"

    def onStateChangedDoSavePhysicallyCapturedImagesComponent(self):
        isChecked = self.__getDoSavePhysicallyCapturedImagesComponent().isChecked()
        if isChecked:
            print('checked')
        else:
            print('unchecked')
        ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings().setDoSavePhysicallyCapturedImages(isChecked)

    # Filename convention inside the chosen folder (SPEC_pumpkin_integration.md A.4).
    __FILENAME_BY_ROLE = {
        VirtualCaptureRole.CALIBRATION: 'calibration.png',
        VirtualCaptureRole.REFERENCE: 'reference.png',
        VirtualCaptureRole.SAMPLE: 'sample.png',
    }

    def onClickedOpenPictureButton(self):
        # P4g: on Android the native SAF folder picker backgrounds this heavy app, which the system
        # then reclaims (losing the result). A same-process foreground service keeps the process alive
        # across the picker. No-op on desktop. See docs/SPEC_android_port.md §3.2.
        from sciens.spectracs.logic.appliction.android import AndroidForegroundKeepAlive
        from PySide6.QtWidgets import QApplication
        AndroidForegroundKeepAlive.start()
        QApplication.processEvents()  # let the service reach startForeground before the picker opens
        try:
            folder = QFileDialog.getExistingDirectory(self, 'Select virtual capture image folder')
        finally:
            AndroidForegroundKeepAlive.stop()
        # P4g spike: capture exactly what SAF hands back (path vs content:// URI) — drives the loader.
        print('P4g picker returned: %r' % folder)
        if not folder:
            return
        virtualSettings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        missing = []
        calibrationImage = None
        for role, filename in self.__FILENAME_BY_ROLE.items():
            image = self.__loadImage(folder, filename)
            if image is None or image.isNull():
                missing.append(filename)
                continue
            virtualSettings.setImage(role, image)
            if role == VirtualCaptureRole.CALIBRATION:
                calibrationImage = image
        if calibrationImage is not None:
            self.__getImageViewModule().setImage(calibrationImage)
        if missing:
            print('virtual capture folder is missing: %s' % ', '.join(missing))

    def __loadImage(self, folder, filename):
        """Return a QImage for `filename` in the selected folder. On Android the folder is a SAF
        content:// tree URI (scoped storage — no filesystem access), so build the child DOCUMENT URI
        and read it through a QFile device (Qt's content-URI engine); on desktop it's a plain path."""
        if folder.startswith('content://'):
            return self.__loadContentImage(self.__childDocumentUri(folder, filename), filename)
        path = self.__findImage(folder, filename)
        return QImage(path) if path is not None else None

    def __loadContentImage(self, uri, filename):
        """Load an image from a SAF content:// document URI. Read the bytes through a QFile device
        (Qt's content-URI engine), then decode. Qt's built-in handler covers PNG; the Android Qt build
        ships no JPEG plugin, and some capture files are actually JPEG named *.png (Raspberry Pi
        output) — so on decode failure fall back to Pillow, which is bundled and handles JPEG."""
        from PySide6.QtCore import QFile
        contentFile = QFile(uri)
        if not contentFile.open(QFile.OpenModeFlag.ReadOnly):
            print('P4g load %s: QFile.open FAILED (%s) uri=%s' % (filename, contentFile.errorString(), uri))
            return None
        data = contentFile.readAll()
        contentFile.close()

        image = QImage()
        if image.loadFromData(data):
            return image

        try:
            from PIL import Image
            import io
            pilImage = Image.open(io.BytesIO(bytes(data))).convert('RGBA')
            buffer = pilImage.tobytes('raw', 'RGBA')
            image = QImage(buffer, pilImage.width, pilImage.height, QImage.Format.Format_RGBA8888).copy()
            print('P4g load %s: decoded via Pillow %dx%d' % (filename, pilImage.width, pilImage.height))
            return image
        except Exception as error:
            print('P4g load %s: Pillow fallback failed: %r' % (filename, error))
            return None

    def __childDocumentUri(self, treeUri, filename):
        """Build the SAF child-document content:// URI for a file directly under the picked tree.
        Works for the primary external-storage provider, whose document IDs are path-based
        (`primary:rel/path`), so the child id is just the tree id + '/' + filename."""
        from urllib.parse import quote, unquote
        prefix, _, treeDocIdEncoded = treeUri.partition('/tree/')
        treeDocId = unquote(treeDocIdEncoded)
        childDocId = treeDocId + '/' + filename
        return '%s/tree/%s/document/%s' % (prefix, quote(treeDocId, safe=''), quote(childDocId, safe=''))

    def __findImage(self, folder, filename):
        target = filename.lower()  # PNG-only, case-insensitive match
        for entry in os.listdir(folder):
            if entry.lower() == target:
                return os.path.join(folder, entry)
        return None

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)  # borderless holder (spec C2)

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)  # align nav buttons to content edge (spec C7)
        result.setLayout(layout);

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBackButton)

        return result

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)


