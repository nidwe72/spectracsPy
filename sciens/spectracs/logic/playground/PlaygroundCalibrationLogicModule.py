import os

import numpy
from PySide6.QtGui import QImage

from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import ImageSpectrumAcquisitionLogicModuleParameters
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerRegionOfInterestLogicModule import SpectrometerRegionOfInterestLogicModule
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationAdvancedLogicModule import SpectrometerWavelengthCalibrationAdvancedLogicModule
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import SpectrometerCalibrationProfile
from sciens.spectracs.model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import SpectrometerCalibrationProfileHoughLinesVideoSignal
from sciens.spectracs.model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal


class PlaygroundCalibrationResult:
    def __init__(self, profile, imagePath, imageWidth, imageHeight, nanometerAtX1, nanometerAtX2):
        self.profile = profile
        self.imagePath = imagePath
        self.imageWidth = imageWidth
        self.imageHeight = imageHeight
        self.nanometerAtX1 = nanometerAtX1
        self.nanometerAtX2 = nanometerAtX2

    def polynomial(self):
        return numpy.poly1d([self.profile.interpolationCoefficientA, self.profile.interpolationCoefficientB,
                             self.profile.interpolationCoefficientC, self.profile.interpolationCoefficientD])


class PlaygroundCalibrationLogicModule(Singleton):
    # Fresh, automatic calibration of the bundled Philips CFL capture into a dedicated (transient)
    # playground SpectrometerCalibrationProfile: ROI (Hough band edges + vertical scan) → 1-D intensity
    # profile → advanced predict-and-snap matcher → cubic px→nm coefficients. DB-free (the advanced
    # matcher uses transient CFL master data). Computed once and cached.

    __cachedResult = None

    def calibrationImagePath(self):
        here = os.path.dirname(__file__)
        return os.path.normpath(os.path.join(here, "..", "..", "..", "..", "testSpectra",
                                              "cfl_philips_calibration.png"))

    def calibrate(self) -> PlaygroundCalibrationResult:
        if self.__cachedResult is not None:
            return self.__cachedResult

        imagePath = self.calibrationImagePath()
        image = QImage(imagePath)
        profile = self.calibrateImage(image)
        polynomial = numpy.poly1d([profile.interpolationCoefficientA, profile.interpolationCoefficientB,
                                   profile.interpolationCoefficientC, profile.interpolationCoefficientD])
        self.__cachedResult = PlaygroundCalibrationResult(
            profile, imagePath, image.width(), image.height(),
            float(polynomial(profile.regionOfInterestX1)),
            float(polynomial(profile.regionOfInterestX2)))
        return self.__cachedResult

    def calibrateImage(self, image) -> SpectrometerCalibrationProfile:
        # The reusable core: ROI (Hough band edges + centre-row edge scan) -> 1-D intensity profile ->
        # advanced predict-and-snap matcher -> cubic px->nm coefficients, on ANY QImage. Used both for the
        # bundled CFL (calibrate) and to auto-calibrate a virtual device from its loaded calibration.png.
        roiSignal = SpectrometerCalibrationProfileHoughLinesVideoSignal()
        roiSignal.image = image
        upperLine, lowerLine = SpectrometerRegionOfInterestLogicModule().getHorizontalBoundingLines(roiSignal)
        roiSignal.upperHoughLine = upperLine
        roiSignal.lowerHoughLine = lowerLine
        SpectrometerRegionOfInterestLogicModule().getVerticalBoundingLines(roiSignal)

        profile = SpectrometerCalibrationProfile()
        profile.regionOfInterestX1 = roiSignal.leftBoundingLine.p1().x()
        profile.regionOfInterestY1 = roiSignal.lowerHoughLine.p1().y()
        profile.regionOfInterestX2 = roiSignal.rightBoundingLine.p1().x()
        profile.regionOfInterestY2 = roiSignal.upperHoughLine.p1().y()

        wavelengthSignal = SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal()
        wavelengthSignal.image = image
        wavelengthSignal.model = profile
        parameters = ImageSpectrumAcquisitionLogicModuleParameters()
        parameters.setVideoSignal(wavelengthSignal)
        parameters.setAcquireColors(True)
        spectrum = ImageSpectrumAcquisitionLogicModule().execute(parameters).spectrum

        advanced = SpectrometerWavelengthCalibrationAdvancedLogicModule().match(spectrum)
        profile.interpolationCoefficientA = advanced.interpolationCoefficientA
        profile.interpolationCoefficientB = advanced.interpolationCoefficientB
        profile.interpolationCoefficientC = advanced.interpolationCoefficientC
        profile.interpolationCoefficientD = advanced.interpolationCoefficientD
        return profile
