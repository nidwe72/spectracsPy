import numpy

from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil


class CameraCaptureRenderUtil(Singleton):
    # Renders a spectrum as the sensor would see the dispersed strip — returns a plain numpy RGB array
    # (H, W, 3) uint8, Qt-free (only QColor, no QApplication/widgets). The geometry is faithful to the
    # calibration: x→nm via the px→nm polynomial, the band sits in the ROI (black borders left/right
    # where the captured ~404–635 nm starts/ends), vertically cropped to the band + a thin black margin.
    # Shared by the playground view (wraps it in a QImage) and the PDF report (imshow), so they match.

    def renderStripArray(self, spectrum, calibration, displayWidth=720, bandHeight=78, verticalMargin=16):
        profile = calibration.profile
        polynomial = calibration.polynomial()
        scale = displayWidth / float(calibration.imageWidth)
        displayHeight = bandHeight + 2 * verticalMargin

        left = int(round(profile.regionOfInterestX1 * scale))
        right = int(round(profile.regionOfInterestX2 * scale))
        top = verticalMargin
        bottom = verticalMargin + bandHeight

        values = spectrum.valuesByNanometers
        columns = numpy.arange(left, right)
        nanometers = polynomial(columns / scale)
        baseRed = numpy.zeros(len(columns)); baseGreen = numpy.zeros(len(columns))
        baseBlue = numpy.zeros(len(columns)); fraction = numpy.zeros(len(columns))
        spectralColorUtil = SpectralColorUtil()
        captured = [values.get(int(round(nm)), 0.0) for nm in nanometers if 380.0 <= nm <= 780.0]
        maximum = (max(captured) if len(captured) > 0 else 1.0) or 1.0
        for index, nanometer in enumerate(nanometers):
            if 380.0 <= nanometer <= 780.0:
                color = spectralColorUtil.wavelengthToColor(float(nanometer))
                baseRed[index] = color.red(); baseGreen[index] = color.green(); baseBlue[index] = color.blue()
                fraction[index] = values.get(int(round(nanometer)), 0.0) / maximum

        rows = numpy.arange(top, bottom)
        center = (top + bottom) / 2.0
        verticalFalloff = numpy.exp(-0.5 * ((rows - center) / max(1.0, (bottom - top) * 0.42)) ** 2)

        red = numpy.zeros((displayHeight, displayWidth)); green = numpy.zeros((displayHeight, displayWidth))
        blue = numpy.zeros((displayHeight, displayWidth))
        red[top:bottom, left:right] = numpy.outer(verticalFalloff, baseRed * fraction)
        green[top:bottom, left:right] = numpy.outer(verticalFalloff, baseGreen * fraction)
        blue[top:bottom, left:right] = numpy.outer(verticalFalloff, baseBlue * fraction)

        return numpy.ascontiguousarray(numpy.dstack([numpy.clip(red, 0, 255), numpy.clip(green, 0, 255),
                                                     numpy.clip(blue, 0, 255)]).astype(numpy.uint8))
