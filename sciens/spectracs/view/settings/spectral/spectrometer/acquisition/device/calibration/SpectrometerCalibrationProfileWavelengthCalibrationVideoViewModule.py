from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPixmap, QPen, QBrush
from PySide6.QtWidgets import QApplication, QMessageBox

from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule

from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import \
    ImageSpectrumAcquisitionLogicModuleParameters
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModule import \
    SpectrometerWavelengthCalibrationLogicModule
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleParameters import \
    SpectrometerWavelengthCalibrationLogicModuleParameters
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleResult import \
    SpectrometerWavelengthCalibrationLogicModuleResult
from sciens.spectracs.logic.spectral.acquisition.device.calibration.CalibrationAlgorithm import CalibrationAlgorithm
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationConsensusLogicModule import \
    SpectrometerWavelengthCalibrationConsensusLogicModule
from sciens.spectracs.logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from sciens.spectracs.logic.spectral.util.SpectrumUtil import SpectrumUtil
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile
from sciens.spectracs.model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from sciens.spectracs.model.signal import SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.view.application.widgets.graphicsScene.BaseGraphicsLineItem import BaseGraphicsLineItem
from sciens.spectracs.view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule

from scipy.signal import find_peaks


class SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule(
    BaseVideoViewModule[SpectrometerCalibrationProfileHoughLinesVideoSignal]):
    __model: SpectrometerCalibrationProfile = None

    __spectrum: Spectrum = None

    __algorithm: str = CalibrationAlgorithm.HEURISTIC

    spectrometerWavelengthCalibrationLogicModule: SpectrometerWavelengthCalibrationLogicModule = None

    @property
    def spectrum(self):
        return self.__spectrum

    @spectrum.setter
    def spectrum(self, spectrum):
        self.__spectrum = spectrum

    def setAlgorithm(self, algorithm):
        self.__algorithm = algorithm

    def getAlgorithm(self):
        return self.__algorithm

    def _runHeuristicMatcher(self, videoSignal):
        logicModule = SpectrometerWavelengthCalibrationLogicModule()
        parameters = SpectrometerWavelengthCalibrationLogicModuleParameters()
        logicModule.moduleParameters = parameters
        parameters.videoSignal = videoSignal
        logicModule.execute()
        return logicModule.getModuleResult()

    def _applyCoefficients(self, model, a, b, c, d):
        model.interpolationCoefficientA = a
        model.interpolationCoefficientB = b
        model.interpolationCoefficientC = c
        model.interpolationCoefficientD = d

    def _runCalibrationMatcher(self, videoSignal):
        # The "Heuristic" option runs a CONSENSUS: the simple heuristic produces the five anchor lines,
        # cross-checked by the advanced (predict-and-snap) cubic + colour + green-doublet to raise
        # confidence. Lines that fail a check are reported so the user can re-check before trusting them.
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = SpectrometerWavelengthCalibrationConsensusLogicModule().match(videoSignal)
            lines = result.getSpectralLines()
            if len(lines) < 4:
                QMessageBox.warning(
                    self, "Calibration failed",
                    "Could not detect the calibration lines. Check the spectrum and Region of Interest.")
                return SpectrometerWavelengthCalibrationLogicModuleResult()

            coefficients = SpectralLineUtil().polyfit(lines).coefficients.tolist()
            self._applyCoefficients(videoSignal.model, coefficients[0], coefficients[1],
                                    coefficients[2], coefficients[3])
            videoSignal.model.spectralLines = lines

            if result.getUncertainLines():
                detail = "\n".join("  %.1f nm: %s" % (nanometer, ", ".join(reasons))
                                   for nanometer, reasons in result.getUncertainLines())
                QMessageBox.warning(
                    self, "Low-confidence calibration lines",
                    "The cross-check flagged these line(s) as uncertain — re-check the spectrum / Region "
                    "of Interest before trusting the calibration:\n" + detail)
            return result
        finally:
            QApplication.restoreOverrideCursor()

    def handleVideoThreadSignal(self, videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal):

        peaks = None

        for item in self.scene.items():
            if isinstance(item, BaseGraphicsLineItem):
                self.scene.removeItem(item)

        if videoSignal.currentFrameIndex == 1:
            self.spectrum = Spectrum()

        spectrometerWavelengthCalibrationLogicModuleResult: SpectrometerWavelengthCalibrationLogicModuleResult = None

        if videoSignal.currentFrameIndex == videoSignal.framesCount-1:

            videoSignal.spectrum = self.spectrum

            spectrometerWavelengthCalibrationLogicModuleResult = self._runCalibrationMatcher(videoSignal)

        else:

            imageAcquisitionLogicModule = ImageSpectrumAcquisitionLogicModule()
            logicModuleParameters = ImageSpectrumAcquisitionLogicModuleParameters()
            logicModuleParameters.setVideoSignal(videoSignal)
            logicModuleParameters.spectrum = self.spectrum
            logicModuleParameters.setAcquireColors(True)
            imageAcquisitionLogicModule.execute(logicModuleParameters)

            SpectrumUtil().mean(self.spectrum)
            SpectrumUtil().smooth(self.spectrum)

            for prominence in range(1, 100):
                peaks, _ = find_peaks(list(self.spectrum.valuesByNanometers.values()), distance=3, width=3,
                                      rel_height=0.5, prominence=prominence)
                if len(peaks) == 10:
                    break

            # debugPurpose
            # plt.title("spectrum")
            # plt.xlabel("X axis")
            # plt.ylabel("Y axis")
            # plt.plot(list(self.spectrum.valuesByNanometers.keys()), list(self.spectrum.valuesByNanometers.values()), color="blue")
            # plt.show()

        image = videoSignal.image
        somePixmap = QPixmap.fromImage(image)
        self.imageItem.setPixmap(somePixmap)

        if peaks is not None:

            for peakIndex in peaks.tolist():
                lineItem = BaseGraphicsLineItem()
                lineItem.setLine(peakIndex, 0, peakIndex, videoSignal.image.height())
                pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryTextColor()), 1)
                pen.setStyle(Qt.PenStyle.DotLine)
                lineItem.setPen(pen)

                self.scene.addItem(lineItem)

        if spectrometerWavelengthCalibrationLogicModuleResult is not None:
            spectralLines = spectrometerWavelengthCalibrationLogicModuleResult.getSpectralLines()
            for spectralLine in spectralLines:
                lineItem = BaseGraphicsLineItem()
                lineItem.setLine(spectralLine.pixelIndex, 0, spectralLine.pixelIndex, videoSignal.image.height())
                pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryTextColor()), 3)
                pen.setStyle(Qt.PenStyle.DotLine)
                lineItem.setPen(pen)

                self.scene.addItem(lineItem)

        self._fitInView()
        return

    def _fitInView(self):
        regionOfInterestY2 = self.getModel().regionOfInterestY2
        if regionOfInterestY2 is not None:

            topLeft = QPointF(0, regionOfInterestY2)
            if topLeft is not None:

                imageWidth = self.imageItem.pixmap().width()
                if imageWidth > 0:
                    bottomRight = QPointF(imageWidth, self.getModel().regionOfInterestY1)
                    fitRectangle = QRectF()
                    fitRectangle.setBottomLeft(topLeft)
                    fitRectangle.setBottomRight(bottomRight)
                    self.videoWidget.fitInView(fitRectangle, Qt.AspectRatioMode.KeepAspectRatio)
                    self.videoWidget.centerOn(topLeft)
                    self.videoWidget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            super()._fitInView()

    def initialize(self):
        super().initialize()

    def setModel(self, model: SpectrometerCalibrationProfile):
        self.__model = model
        if self.spectrometerWavelengthCalibrationLogicModule is None:
            self.spectrometerWavelengthCalibrationLogicModule = SpectrometerWavelengthCalibrationLogicModule()
        self.spectrometerWavelengthCalibrationLogicModule.setModel(model)

    def getModel(self) -> SpectrometerCalibrationProfile:
        return self.__model
