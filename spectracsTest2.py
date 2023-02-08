import os

import pandas as pd
from matplotlib import pyplot as plt
from numpy import float64, int64, float32
from pyspectra.transformers.spectral_correction import sav_gol
from rascal.atlas import Atlas
from rascal.calibrator import Calibrator

from logic.spectral.util.SpectralLineMasterDataUtil import SpectralLineMasterDataUtil
from model.spectral.Spectrum import Spectrum

from scipy.signal import find_peaks, peak_prominences

from rascal.util import refine_peaks

import numpy as np

from astropy.io import fits


from pyspectra.readers.read_dx import read_dx



class RascalLogicModule:

    def createAtlas(self):

        result=Atlas()

        spectralLineMasterDatasByNames = SpectralLineMasterDataUtil().createTransientSpectralLineMasterDatasByNames()

        elements=[]
        wavelengths=[]
        intensities=[]

        maxNanometer = 650
        # maxNanometer=740

        for spectralLineMasterData in spectralLineMasterDatasByNames.values():
            nanometer = spectralLineMasterData.nanometer
            if nanometer<maxNanometer:
                elements.append('Hg')
                wavelengths.append(nanometer*10)
                intensities.append(spectralLineMasterData.intensity)

        elementsArray=np.asarray(elements,str)
        wavelengthsArray=np.asarray(wavelengths, float64)
        intensitiesArray = np.asarray(intensities, float64)

        result.add_user_atlas(elementsArray,wavelengthsArray,intensitiesArray)

        smoother = sav_gol()


        return result

        # self,
        # elements,
        # wavelengths,
        # intensities=None,
        # vacuum=False,
        # pressure=101325.0,
        # temperature=273.15,
        # relative_humidity=0.0,

    def execute(self,spectrum:Spectrum):
        #self.testFoo()



        atlas = self.createAtlas()

        nanometers = list(spectrum.valuesByNanometers.values())
        nanometersArray=np.asarray(nanometers,int64)
        nanometersArrayFloat = np.asarray(nanometers, float32)
        nanometersArrayFloat=nanometersArrayFloat*10

        # plt.title("captured")
        # plt.xlabel("X axis")
        # plt.ylabel("Y axis")
        # plt.plot(list(spectrum.valuesByNanometers.keys()), list(spectrum.valuesByNanometers.values()), color="red")
        # figure = plt.gcf()
        # figure.set_size_inches(19.20, 10.80)
        # plt.show()

        # spectrumValuesNpArray=np.array(list(spectrum.valuesByNanometers.values()))
        # df = pd.DataFrame(list(spectrum.valuesByNanometers.items()), columns=['column1', 'column2'])

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



        smoothedFrame.transpose().plot()
        figure = plt.gcf()
        figure.set_size_inches(19.20, 10.80)
        # plt.savefig('/home/nidwe/development/spectracs/spectracs-evaluations/20230120/sample_step1_original.png',
        #             dpi=100)
        plt.show()

        originalWavelengths = smoothedFrame.axes[1].values
        originalValues = smoothedFrame.values

        nanometers = smoothedFrame.values.tolist()[0]
        nanometersArrayFloat = np.asarray(nanometers, float32)
        nanometersArrayFloat=nanometersArrayFloat*10


        # peaks, _ = find_peaks(nanometersArrayFloat, distance=5, height=5, width=5, prominence=10)
        # prominences = peak_prominences(nanometersArrayFloat, peaks)[0]






        # peaks, _ = find_peaks(nanometersArray, height=300, prominence=200, distance=5)

        #height = 50 * 10
        peaks, _ = find_peaks(nanometersArrayFloat, distance=10, width=3, rel_height=0.5,prominence=10)

        # prominences = peak_prominences(spectrumValuesNpArray, peaks)[0]


        peaks = refine_peaks(nanometersArrayFloat, peaks, window_width=5)

        c = Calibrator(peaks, spectrum=nanometersArrayFloat)
        c.plot_arc()
        c.set_hough_properties(
            num_slopes=10000,
            range_tolerance=500.0,
            xbins=1000,
            ybins=1000,
            # min_wavelength=405.4*10,
            # max_wavelength=631.1*10,
            min_wavelength=380 * 10,
            max_wavelength=640 * 10,

        )
        c.set_ransac_properties(sample_size=5, top_n_candidate=5, filter_close=True)

        c.set_atlas(atlas, candidate_tolerance=5.0)

        c.do_hough_transform()

        # Run the wavelength calibration
        (
            best_p,
            matched_peaks,
            matched_atlas,
            rms,
            residual,
            peak_utilisation,
            atlas_utilisation,
        ) = c.fit(max_tries=20000)

        # Plot the solution
        c.plot_fit(
            best_p, nanometersArrayFloat, plot_atlas=True, log_spectrum=False, tolerance=5.0
        )

        return

    def testFoo(self):

        # Load the LT SPRAT data
        base_dir = os.path.dirname(__file__)
        fits_file = fits.open(
            os.path.join(base_dir, "/home/nidwe/development/tryOut/rascal/examples/data_lt_sprat/v_a_20190516_57_1_0_1.fits")
        )[0]

        spectrum2D = fits_file.data

        temperature = fits_file.header["REFTEMP"]
        pressure = fits_file.header["REFPRES"] * 100.0
        relative_humidity = fits_file.header["REFHUMID"]

        # Collapse into 1D spectrum between row 110 and 120
        spectrum = np.median(spectrum2D[110:120], axis=0)

        # Identify the peaks
        peaks, _ = find_peaks(spectrum, height=300, prominence=200, distance=5)
        peaks = refine_peaks(spectrum, peaks, window_width=5)

        # Initialise the calibrator
        c = Calibrator(peaks, spectrum=spectrum)
        c.plot_arc()
        c.set_hough_properties(
            num_slopes=5000,
            range_tolerance=500.0,
            xbins=200,
            ybins=200,
            min_wavelength=3500.0,
            max_wavelength=6500.0,
        )
        c.set_ransac_properties(sample_size=5, top_n_candidate=5, filter_close=True)

        atlas = Atlas(
            elements=["Xe"],
            min_intensity=100.0,
            min_distance=10,
            min_atlas_wavelength=3500.0,
            max_atlas_wavelength=650.0,
            range_tolerance=500.0,
            pressure=pressure,
            temperature=temperature,
            relative_humidity=relative_humidity,
        )

        atlas2 = Atlas()
        #todo: supply lines of CFL spectrum
        # atlas2.add_user_atlas()


        elements = atlas.get_elements()


        c.set_atlas(atlas, candidate_tolerance=5.0)

        c.do_hough_transform()

        # Run the wavelength calibration
        (
            best_p,
            matched_peaks,
            matched_atlas,
            rms,
            residual,
            peak_utilisation,
            atlas_utilisation,
        ) = c.fit(max_tries=500)

        # Plot the solution
        c.plot_fit(
            best_p, spectrum, plot_atlas=True, log_spectrum=False, tolerance=5.0
        )

        # Show the parameter space for searching possible solution
        c.plot_search_space()

        print("Stdev error: {} A".format(residual.std()))
        print("Peaks utilisation rate: {}%".format(peak_utilisation * 100))
        print("Atlas utilisation rate: {}%".format(atlas_utilisation * 100))

        return




