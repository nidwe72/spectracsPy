#Import basic libraries
import colorsys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import spectres
from BaselineRemoval import BaselineRemoval
from colour import SpectralDistribution, MSDS_CMFS, SDS_ILLUMINANTS, sd_to_XYZ, XYZ_to_RGB, XYZ_to_xy, RGB_COLOURSPACES, \
    XYZ_to_sRGB
from colour.plotting import plot_single_sd, plot_sds_in_chromaticity_diagram_CIE1931
from luxpy.toolboxes.dispcal import xyz_to_rgb
from pyspectra.readers.read_dx import read_dx

from luxpy import spd, spd_to_xyz

from pyspectra.transformers.spectral_correction import sav_gol

# spc=read_spc('/home/nidwe/development/spectracs/spectracs-evaluations/20230111/oil_weinhandel.spc')
# spc.plot()
# plt.xlabel("nm")
# plt.ylabel("Abs")
# plt.grid(True)
# print(spc.head())




#Instantiate an object
from rgbxy import Converter

Foss_single= read_dx()
# Run  read method
#df=Foss_single.read(file='/home/nidwe/development/spectracs/spectracs-evaluations/20230114/oil_wanhandel_processed.dx')
#df=Foss_single.read(file='/home/nidwe/development/spectracs/spectracs-evaluations/20230114/red_mean.dx')
#df=Foss_single.read(file='/home/nidwe/development/spectracs/spectracs-evaluations/20230114/oil_spar_processed.dx')
#df=Foss_single.read(file='/home/nidwe/development/spectracs/spectracs-evaluations/20230114/oil_sparSteirisch_processed.dx')
#df=Foss_single.read(file='/home/nidwe/development/spectracs/spectracs-evaluations/20230114/oil_lugitsch_processed.dx')
#df=Foss_single.read(file='/home/nidwe/development/spectracs/spectracs-evaluations/20230114/oil_hofer_processed.dx')


#df=Foss_single.read(file='/home/nidwe/development/spectracs/spectracs-evaluations/20230120/oil_weinhandel_mean.dx')
#df=Foss_single.read(file='/home/nidwe/development/spectracs/spectracs-evaluations/20230120/oil_lugitsch_mean.dx')
df=Foss_single.read(file='/home/nidwe/development/spectracs/spectracs-evaluations/20230120/oil_spar_mean.dx')



#df.transpose().plot()



smoother = sav_gol()
smoothedFrame=smoother.transform(df,10,3)
smoothedFrame=smoother.transform(smoothedFrame,10,3)
smoothedFrame=smoother.transform(smoothedFrame,10,3)
#plt.title("original")

smoothedFrame.transpose().plot()
figure = plt.gcf()
figure.set_size_inches(19.20, 10.80)
plt.savefig('/home/nidwe/development/spectracs/spectracs-evaluations/20230120/sample_step1_original.png',dpi=100)
plt.show()



originalWavelengths=smoothedFrame.axes[1].values
originalValues=smoothedFrame.values

newWavelengths=np.asarray(range(380,780))

newWavelengths=np.arange(380,781,1)
newWavelengths=newWavelengths.flatten()

newValues=spectres.spectres(newWavelengths,originalWavelengths,originalValues)
newValues=newValues.flatten()
newValuesArray=newValues.tolist()

#newValues=newValues.reshape((400,0))


plt.title("smoothed and rebinned")
plt.xlabel("X axis")
plt.ylabel("Y axis")
plt.plot(newWavelengths, newValues, color ="red")
figure = plt.gcf()
figure.set_size_inches(19.20, 10.80)
plt.savefig('/home/nidwe/development/spectracs/spectracs-evaluations/20230120/sample_step2_smoothedAndRebinned.png',dpi=100)
plt.show()


baselineRemoval=BaselineRemoval(newValues)
# Modpoly_output=baseObj.ModPoly(polynomial_degree)
# Imodpoly_output=baseObj.IModPoly(polynomial_degree)
newValues=baselineRemoval.ZhangFit()
plt.title("baseline removed")
plt.xlabel("X axis")
plt.ylabel("Y axis")
plt.plot(newWavelengths, newValues, color ="green")
figure = plt.gcf()
figure.set_size_inches(19.20, 10.80)
plt.savefig('/home/nidwe/development/spectracs/spectracs-evaluations/20230120/sample_step3_baselineCorrected.png',dpi=100)
plt.show()


maximalValue=newValues.max()
newValues=newValues/maximalValue




foo=newWavelengths.tolist()
bar=newValues.tolist()



export=np.stack((np.array(newWavelengths.tolist()),np.array(newValues.tolist())),axis=-1)

plt.title("export")
plt.xlabel("X axis")
plt.ylabel("Y axis")
plt.plot(newWavelengths, newValues, color ="blue")
plt.show()

data_frame = pd.DataFrame(export)
spectrum = spd(data_frame)
xyz = spd_to_xyz(data_frame)


#export.tofile('/home/nidwe/development/spectracs/spectracs-evaluations/20230111/oil_weinhandel.csv', sep=',', format='%f')

plt.show()


#dict = dict(enumerate(export.flatten(), 1))

dict = dict(zip(newWavelengths.tolist(), newValues.tolist()))

spectralDistribution = SpectralDistribution(dict)


plot_single_sd(spectralDistribution, y_label='SPD (W/nm)', x_label='Wavelength (nm)', title='SBM-40-HC-RGBWW Simulation');
figure = plt.gcf()
figure.set_size_inches(19.20, 10.80)
plt.savefig('/home/nidwe/development/spectracs/spectracs-evaluations/20230120/sample_step4_preprocessedFinal.png',dpi=100)


cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
plot_sds_in_chromaticity_diagram_CIE1931([cmfs, spectralDistribution]);
figure = plt.gcf()
figure.set_size_inches(19.20, 10.80)
plt.savefig('/home/nidwe/development/spectracs/spectracs-evaluations/20230120/sample_step5_evaluatedCie.png',dpi=100)


illuminant = SDS_ILLUMINANTS["D65"]
to_xyz = sd_to_XYZ(spectralDistribution, cmfs, illuminant,method='Integration')
xy = XYZ_to_xy(to_xyz)

converter = Converter()

rgb = converter.xy_to_rgb(xy[0], xy[1])

hls = colorsys.rgb_to_hls(rgb[0]/255.0,rgb[1]/255.0,rgb[2]/255.0)
hue=360.0/(1.0/hls[0])
lightness=hls[1]*100.0
saturation=hls[2]*100.0

rgb2 = colorsys.hls_to_rgb(hls[0], 0.20, hls[2])

rgb3=[rgb2[0]*255.0,rgb2[1]*255.0,rgb2[2]*255.0]


plt.title("color")
plt.xlabel("")
plt.ylabel("")
plt.imshow([[(rgb2[0], rgb2[1], rgb2[2])]])
figure = plt.gcf()
figure.set_size_inches(19.20, 10.80)
plt.savefig('/home/nidwe/development/spectracs/spectracs-evaluations/20230120/sample_step6_evaluatedRgb.png',dpi=100)

#plt.show()

plt.show(block=True)


print('stop...')
