import numpy
import numpy as np
from matplotlib import pyplot as plt
from pyspectra.readers.read_dx import read_dx
from pyspectra.transformers.spectral_correction import sav_gol
from scipy.signal import savgol_filter


class SpectracsTest3:

    def test(self):

        Foss_single = read_dx()

        df = Foss_single.read(file='/home/nidwe/development/spectracs/spectracs-evaluations/20230207/tornado640.dx')

        # todo: read dx spectrum file (the one prepared by spectragryph on windows for getting the atlas lines ) and smooth it
        # !!!!!THE DX SPECTRUM IS ALSO ALREADY AVERAGED!!!!!!
        # prepare array to be peaked and run rascal
        # look whether peaks are detected that way
        smoother = sav_gol()
        smoothedFrame = smoother.transform(df, 10, 3)
        smoothedFrame = smoother.transform(smoothedFrame, 10, 3)
        smoothedFrame = smoother.transform(smoothedFrame, 10, 3)

        originalWavelengths=numpy.asarray(np.array(df.axes[:].pop())).flatten()
        originalValues = smoothedFrame.values.flatten()


        originalWavelengths = df.axes[1].values
        originalValues = smoothedFrame.values.flatten()

        smoothedValues = savgol_filter(originalValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)

        plt.title("originalValues")
        plt.xlabel("X axis")
        plt.ylabel("Y axis")
        plt.plot(originalWavelengths, originalValues, color="blue")
        plt.show()


        plt.title("smoothedValues")
        plt.xlabel("X axis")
        plt.ylabel("Y axis")
        plt.plot(originalWavelengths, smoothedValues, color="blue")
        plt.show()

        return


SpectracsTest3().test()




