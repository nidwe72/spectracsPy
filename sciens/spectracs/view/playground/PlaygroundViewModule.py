import colorsys

import numpy
import pyqtgraph
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QTabWidget, QWidget, QLabel, QVBoxLayout, QScrollArea

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.playground.CameraCaptureRenderUtil import CameraCaptureRenderUtil
from sciens.spectracs.logic.playground.PlaygroundCalibrationLogicModule import PlaygroundCalibrationLogicModule
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModule import LedReferenceSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModuleParameters import LedReferenceSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModule import OilSampleSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModuleParameters import OilSampleSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.PlaygroundDemoOils import PLAYGROUND_DEMO_OILS
from sciens.spectracs.logic.spectral.synthesis.SpectrumSynthesisUtil import SpectrumSynthesisUtil
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from sciens.spectracs.logic.spectral.util.SpectrumUtil import SpectrumUtil
from sciens.spectracs.logic.spectral.verdict.VerdictLogicModule import VerdictLogicModule
from sciens.spectracs.logic.spectral.verdict.VerdictLogicModuleParameters import VerdictLogicModuleParameters
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget

_LED_PEN_COLORS = ["#9b59b6", "#e67e22", "#8e44ad", "#3498db", "#2ecc71", "#c0392b", "#d35400"]


class PlaygroundViewModule(PageWidget):
    """Master-only dev bench: synthesises one full run (LED reference -> 3 oils -> transmission/
    absorption -> colour/verdict) and shows it across flat tabs. Computed lazily on first show."""

    tabWidget: QTabWidget = None
    calibrationImageLabel: QLabel = None
    calibrationInfoLabel: QLabel = None
    ledSetupPlot = None
    referencePlot = None
    oilPlot = None
    absorptionPlot = None
    cameraContainer: QWidget = None
    resultsContainer: QWidget = None
    __populated = False
    __keptImages = None

    def _getPageTitle(self):
        return "Playground"

    def __makePlot(self):
        plot = pyqtgraph.PlotWidget()
        plot.setBackground("#191919")
        plot.addLegend()
        plot.setLabel("bottom", "wavelength [nm]")
        plot.setLabel("left", "intensity")
        return plot

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        if self.tabWidget is None:
            self.__keptImages = []
            self.tabWidget = QTabWidget()

            calibrationTab = QWidget(); calibrationLayout = QVBoxLayout(); calibrationTab.setLayout(calibrationLayout)
            self.calibrationInfoLabel = QLabel("…")
            self.calibrationImageLabel = QLabel(); self.calibrationImageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            calibrationLayout.addWidget(self.calibrationInfoLabel)
            calibrationLayout.addWidget(self.calibrationImageLabel, stretch=1)
            self.tabWidget.addTab(calibrationTab, "Calibration (CFL)")

            self.ledSetupPlot = self.__makePlot()
            self.tabWidget.addTab(self.ledSetupPlot, "LED setup")

            self.referencePlot = self.__makePlot()
            self.tabWidget.addTab(self.referencePlot, "Reference spectrum")

            self.oilPlot = self.__makePlot()
            self.tabWidget.addTab(self.oilPlot, "Oil spectra")

            self.absorptionPlot = self.__makePlot()
            self.absorptionPlot.setLabel("left", "absorbance A = -log10(T)")
            self.tabWidget.addTab(self.absorptionPlot, "Absorption")

            cameraScroll = QScrollArea(); cameraScroll.setWidgetResizable(True)
            self.cameraContainer = QWidget(); self.cameraContainer.setLayout(QVBoxLayout())
            cameraScroll.setWidget(self.cameraContainer)
            self.tabWidget.addTab(cameraScroll, "Camera capture")

            resultsTab = QWidget(); resultsOuterLayout = QVBoxLayout(); resultsTab.setLayout(resultsOuterLayout)
            self.resultsContainer = QWidget(); self.resultsContainer.setLayout(QGridLayout())
            resultsOuterLayout.addStretch(1)
            resultsOuterLayout.addWidget(self.resultsContainer, alignment=Qt.AlignmentFlag.AlignHCenter)
            resultsOuterLayout.addStretch(1)
            self.tabWidget.addTab(resultsTab, "Measured vs target")

        result["tabs"] = self.tabWidget
        return result

    def showEvent(self, event):
        super().showEvent(event)
        if not self.__populated and self.tabWidget is not None:
            self.__populated = True
            self.__populate()

    def __populate(self):
        # --- calibration (fresh, automatic) ---
        calibration = PlaygroundCalibrationLogicModule().calibrate()
        profile = calibration.profile
        self.calibrationInfoLabel.setText(
            "Fresh automatic CFL calibration — ROI (x %d–%d, y %d–%d);  px→nm cubic A=%.3e B=%.3e C=%.4f D=%.2f;  "
            "nm range %.1f … %.1f" % (
                profile.regionOfInterestX1, profile.regionOfInterestX2, profile.regionOfInterestY2,
                profile.regionOfInterestY1, profile.interpolationCoefficientA, profile.interpolationCoefficientB,
                profile.interpolationCoefficientC, profile.interpolationCoefficientD,
                calibration.nanometerAtX1, calibration.nanometerAtX2))
        pixmap = QPixmap.fromImage(QImage(calibration.imagePath))
        if not pixmap.isNull():
            self.calibrationImageLabel.setPixmap(pixmap.scaledToWidth(720, Qt.TransformationMode.SmoothTransformation))

        # --- reference + LED setup ---
        reference = LedReferenceSynthesisLogicModule().synthesize(LedReferenceSynthesisLogicModuleParameters()).getSpectrum()
        referenceNanometers = sorted(reference.valuesByNanometers.keys())
        referenceValues = [reference.valuesByNanometers[nm] for nm in referenceNanometers]
        self.referencePlot.plot(referenceNanometers, referenceValues, pen=pyqtgraph.mkPen("#5fa86a", width=2),
                                name="LED reference R(λ)")

        synthesisAxis = numpy.asarray(referenceNanometers, float)
        for index, (name, spd) in enumerate(SpectrumSynthesisUtil().perLedSpectra(nanometers=referenceNanometers)):
            self.ledSetupPlot.plot(referenceNanometers, list(spd),
                                   pen=pyqtgraph.mkPen(_LED_PEN_COLORS[index % len(_LED_PEN_COLORS)], width=1.5),
                                   name=name)
        self.ledSetupPlot.plot(referenceNanometers, referenceValues, pen=pyqtgraph.mkPen("#ffffff", width=2.5),
                               name="overall reference R(λ)")

        # --- camera capture: REFERENCE strip (real frame geometry), vertically centred ---
        self.cameraContainer.layout().addStretch(1)
        self.__addCameraStrip("REFERENCE  (LED light through the blank)", reference, calibration)

        # --- 3 oils -> samples, transmission, absorption, colour, verdict ---
        resultsLayout = self.resultsContainer.layout()
        for column, heading in enumerate(["oil", "measured", "target", "hue", "verdict"]):
            resultsLayout.addWidget(self.__headingLabel(heading), 0, column)

        for row, demoOil in enumerate(PLAYGROUND_DEMO_OILS, start=1):
            parameters = OilSampleSynthesisLogicModuleParameters()
            parameters.setReference(reference); parameters.setTargetHue(demoOil.targetHue)
            sampleResult = OilSampleSynthesisLogicModule().synthesize(parameters)
            sample = sampleResult.getSpectrum()
            measuredHue = sampleResult.getAchievedHue()

            transmission = SpectrumUtil().transmission(reference, sample)
            absorption = SpectrumUtil().absorption(reference, sample)
            measuredColor = SpectralColorUtil().spectrumToColor(transmission)

            verdictParameters = VerdictLogicModuleParameters(); verdictParameters.setHue(measuredHue)
            roastState = VerdictLogicModule().verdict(verdictParameters).getRoastState()

            # S1b: spectrumToColor now returns a Qt-free SpectralColor. `lighter()` is a Qt colour-manipulation
            # convenience and mkPen wants a QColor regardless, so the VIEW converts — rather than SpectralColor
            # growing a faithful port of QColor::lighter (HSV value scaling with its saturation-overflow quirk).
            # Qt adapters belong in the host; the value type stays minimal.
            penColor = QColor.fromRgb(measuredColor.red(), measuredColor.green(), measuredColor.blue()).lighter(160)
            sampleNanometers = sorted(sample.valuesByNanometers.keys())
            self.oilPlot.plot(sampleNanometers, [sample.valuesByNanometers[nm] for nm in sampleNanometers],
                              pen=pyqtgraph.mkPen(penColor, width=2), name=demoOil.label)
            absorptionNanometers = sorted(absorption.valuesByNanometers.keys())
            self.absorptionPlot.plot(absorptionNanometers,
                                     [absorption.valuesByNanometers[nm] for nm in absorptionNanometers],
                                     pen=pyqtgraph.mkPen(penColor, width=2), name=demoOil.label)
            self.__addCameraStrip("%s  SAMPLE  (LED light through the oil)" % demoOil.label, sample, calibration)

            resultsLayout.addWidget(QLabel(demoOil.label), row, 0)
            resultsLayout.addWidget(self.__swatch(measuredColor), row, 1)
            resultsLayout.addWidget(self.__swatch(self.__targetColor(demoOil.targetHue)), row, 2)
            resultsLayout.addWidget(QLabel("%.0f°" % measuredHue), row, 3)
            resultsLayout.addWidget(QLabel(roastState.value), row, 4)
        resultsLayout.setRowStretch(len(PLAYGROUND_DEMO_OILS) + 1, 1)
        self.cameraContainer.layout().addStretch(1)

    def __addCameraStrip(self, label, spectrum, calibration):
        captionLabel = QLabel(label); captionLabel.setProperty("sectionLabel", True)
        captionLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        imageLabel = QLabel(); imageLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        imageLabel.setPixmap(QPixmap.fromImage(self.__cameraStripImage(spectrum, calibration)))
        self.cameraContainer.layout().addWidget(captionLabel)
        self.cameraContainer.layout().addWidget(imageLabel)

    def __cameraStripImage(self, spectrum, calibration) -> QImage:
        # The dispersed-strip render lives in the shared CameraCaptureRenderUtil (returns a numpy RGB
        # array) so the playground and the PDF report show identical strips. Here we just wrap it in a
        # QImage for display.
        rgb = CameraCaptureRenderUtil().renderStripArray(spectrum, calibration)
        height, width, _ = rgb.shape
        self.__keptImages.append(rgb)
        return QImage(rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888).copy()

    def __headingLabel(self, text):
        label = QLabel(text); label.setProperty("sectionLabel", True)
        return label

    def __swatch(self, color):
        # QColor or SpectralColor — both expose name() (S1b).
        label = QLabel(); label.setFixedSize(120, 36)
        label.setStyleSheet("background-color: %s; border: 1px solid #5A5A5A;" % color.name())
        return label

    def __targetColor(self, targetHue: float) -> QColor:
        red, green, blue = colorsys.hls_to_rgb(targetHue / 360.0, 0.20, 0.85)
        return QColor.fromRgbF(red, green, blue)

    def createNavigationGroupBox(self):
        result = QGroupBox(""); result.setProperty("plain", True)
        layout = QGridLayout(); layout.setSpacing(Metrics.S); layout.setContentsMargins(0, 0, 0, 0)
        result.setLayout(layout)
        backButton = QPushButton(); backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBackButton)
        return result

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)
