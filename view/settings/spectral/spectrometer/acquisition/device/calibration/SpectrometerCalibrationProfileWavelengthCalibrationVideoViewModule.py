from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPixmap, QPen, QBrush

from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import \
    ImageSpectrumAcquisitionLogicModuleParameters
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModule import \
    SpectrometerWavelengthCalibrationLogicModule
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleParameters import \
    SpectrometerWavelengthCalibrationLogicModuleParameters
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleResult import \
    SpectrometerWavelengthCalibrationLogicModuleResult
from sciens.spectracs.logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from sciens.spectracs.logic.spectral.util.SpectrumUtil import SpectrumUtil
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile
from sciens.spectracs.model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from sciens.spectracs.model.signal import SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from view.application.widgets.graphicsScene.BaseGraphicsLineItem import BaseGraphicsLineItem
from view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule

from scipy.signal import find_peaks


class SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule(
    BaseVideoViewModule[SpectrometerCalibrationProfileHoughLinesVideoSignal]):
    __model: SpectrometerCalibrationProfile = None

    __spectrum: Spectrum = None

    spectrometerWavelengthCalibrationLogicModule: SpectrometerWavelengthCalibrationLogicModule = None

    @property
    def spectrum(self):
        return self.__spectrum

    @spectrum.setter
    def spectrum(self, spectrum):
        self.__spectrum = spectrum

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

            spectrometerWavelengthCalibrationLogicModule = SpectrometerWavelengthCalibrationLogicModule()
            spectrometerWavelengthCalibrationLogicModuleParameters = SpectrometerWavelengthCalibrationLogicModuleParameters()
            spectrometerWavelengthCalibrationLogicModule.moduleParameters = spectrometerWavelengthCalibrationLogicModuleParameters
            spectrometerWavelengthCalibrationLogicModuleParameters.videoSignal = videoSignal
            spectrometerWavelengthCalibrationLogicModule.execute()
            spectrometerWavelengthCalibrationLogicModuleResult = spectrometerWavelengthCalibrationLogicModule.getModuleResult()

            polynomial = SpectralLineUtil().polyfit(
                spectrometerWavelengthCalibrationLogicModuleResult.getSpectralLines())
            coefficients = polynomial.coefficients.tolist()

            videoSignal.model.interpolationCoefficientA = coefficients[0]
            videoSignal.model.interpolationCoefficientB = coefficients[1]
            videoSignal.model.interpolationCoefficientC = coefficients[2]
            videoSignal.model.interpolationCoefficientD = coefficients[3]

            videoSignal.model.spectralLines = spectrometerWavelengthCalibrationLogicModuleResult.getSpectralLines()

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
                pen = QPen(QBrush(Qt.white), 1)
                pen.setStyle(Qt.PenStyle.DotLine)
                lineItem.setPen(pen)

                self.scene.addItem(lineItem)

        if spectrometerWavelengthCalibrationLogicModuleResult is not None:
            spectralLines = spectrometerWavelengthCalibrationLogicModuleResult.getSpectralLines()
            for spectralLine in spectralLines:
                lineItem = BaseGraphicsLineItem()
                lineItem.setLine(spectralLine.pixelIndex, 0, spectralLine.pixelIndex, videoSignal.image.height())
                pen = QPen(QBrush(Qt.white), 3)
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
