from rascal.atlas import Atlas

from logic.spectral.util.SpectralLineMasterDataUtil import SpectralLineMasterDataUtil
from model.spectral.Spectrum import Spectrum


class RascalLogicModule:

    def createAtlas(self):

        result=Atlas()
        # result.add_user_atlas()

        spectralLineMasterDatasByNames = SpectralLineMasterDataUtil().createTransientSpectralLineMasterDatasByNames()

        return

        # self,
        # elements,
        # wavelengths,
        # intensities=None,
        # vacuum=False,
        # pressure=101325.0,
        # temperature=273.15,
        # relative_humidity=0.0,

    def execute(self,spectrum:Spectrum):
        self.createAtlas()
        return

#
# rascalLogicModule = RascalLogicModule()
# rascalLogicModule.createAtlas()
#
#
#
# # Load the LT SPRAT data
# base_dir = os.path.dirname(__file__)
# fits_file = fits.open(
#     os.path.join(base_dir, "/home/nidwe/development/tryOut/rascal/examples/data_lt_sprat/v_a_20190516_57_1_0_1.fits")
# )[0]
#
# spectrum2D = fits_file.data
#
# temperature = fits_file.header["REFTEMP"]
# pressure = fits_file.header["REFPRES"] * 100.0
# relative_humidity = fits_file.header["REFHUMID"]
#
# # Collapse into 1D spectrum between row 110 and 120
# spectrum = np.median(spectrum2D[110:120], axis=0)
#
# # Identify the peaks
# peaks, _ = find_peaks(spectrum, height=300, prominence=200, distance=5)
# peaks = util.refine_peaks(spectrum, peaks, window_width=5)
#
# # Initialise the calibrator
# c = Calibrator(peaks, spectrum=spectrum)
# c.plot_arc()
# c.set_hough_properties(
#     num_slopes=5000,
#     range_tolerance=500.0,
#     xbins=200,
#     ybins=200,
#     min_wavelength=3500.0,
#     max_wavelength=8000.0,
# )
# c.set_ransac_properties(sample_size=5, top_n_candidate=5, filter_close=True)
#
# atlas = Atlas(
#     elements=["Xe"],
#     min_intensity=100.0,
#     min_distance=10,
#     min_atlas_wavelength=3500.0,
#     max_atlas_wavelength=8000.0,
#     range_tolerance=500.0,
#     pressure=pressure,
#     temperature=temperature,
#     relative_humidity=relative_humidity,
# )
#
# atlas2 = Atlas()
# #todo: supply lines of CFL spectrum
# # atlas2.add_user_atlas()
#
#
# elements = atlas.get_elements()
#
#
# c.set_atlas(atlas, candidate_tolerance=5.0)
#
# c.do_hough_transform()
#
# # Run the wavelength calibration
# (
#     best_p,
#     matched_peaks,
#     matched_atlas,
#     rms,
#     residual,
#     peak_utilisation,
#     atlas_utilisation,
# ) = c.fit(max_tries=500)
#
# # Plot the solution
# c.plot_fit(
#     best_p, spectrum, plot_atlas=True, log_spectrum=False, tolerance=5.0
# )
#
# # Show the parameter space for searching possible solution
# c.plot_search_space()
#
# print("Stdev error: {} A".format(residual.std()))
# print("Peaks utilisation rate: {}%".format(peak_utilisation * 100))
# print("Atlas utilisation rate: {}%".format(atlas_utilisation * 100))

