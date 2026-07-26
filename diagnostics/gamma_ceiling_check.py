"""L5 verification on real data: is the RELATIVE ceiling dormant on normal spectra (as the 3.0 was),
does it still clamp a T->0 spike, and does it survive the gamma scale change?"""
import json, os, pypdf, numpy as np

REPORTS = os.path.join(
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")),
    "spectracs-references", "tmp")
from sciens.spectracs.logic.spectral.absorption.AbsorptionLogicModule import AbsorptionLogicModule
from sciens.spectracs.logic.spectral.absorption.AbsorptionLogicModuleParameters import AbsorptionLogicModuleParameters
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.util.EvaluationColorUtil import EvaluationColorUtil

GAMMA = 2.2
util = EvaluationColorUtil()

def spec(values):
    s = Spectrum(); s.valuesByNanometers = dict(values); return s

def absorbance(reference, sample):
    p = AbsorptionLogicModuleParameters(); p.setReference(spec(reference)); p.setSample(spec(sample))
    return AbsorptionLogicModule().absorption(p).getSpectrum()

def load(name):
    r = pypdf.PdfReader(os.path.join(REPORTS, "measurement_report_%s.pdf" % name))
    w = json.loads(r.attachments["workflow.json"][0])
    ref = sam = None
    for ph in w["phases"]:
        for st in ph.get("steps", []):
            sp = st.get("spectra") or {}
            if "REFERENCE" in sp and ref is None: ref = {float(k): float(v) for k, v in sp["REFERENCE"].items()}
            if "SAMPLE" in sp and sam is None: sam = {float(k): float(v) for k, v in sp["SAMPLE"].items()}
    return ref, sam

def decode(values):
    return {nm: 255.0 * (max(0.0, v) / 255.0) ** GAMMA for nm, v in values.items()}

print("%-16s %7s %7s   %-22s %-22s %-22s" % ("run", "peakA", "cap", "hue/chroma abs=3.0", "hue/chroma RELATIVE", "clamped bins"))
for name in ("NowSBudget", "NowSteirerkraft", "oilK_001", "oilR_001"):
    ref, sam = load(name)
    for label, (r, s) in (("as-is", (ref, sam)), ("gamma", (decode(ref), decode(sam)))):
        a = absorbance(r, s)
        values = sorted(v for v in a.valuesByNanometers.values() if v > 0)
        p95 = values[int(round(0.95 * (len(values) - 1)))]
        cap = util.RELATIVE_CEILING_MULTIPLE * p95
        clamped = sum(1 for v in a.valuesByNanometers.values() if v > cap)
        h1, s1, l1 = util.spectrumToHsl(a, converter="srgb", ceiling=3.0)
        h2, s2, l2 = util.spectrumToHsl(a, converter="srgb", ceiling=util.RELATIVE)
        c1 = (1 - abs(2 * l1 / 100 - 1)) * s1
        c2 = (1 - abs(2 * l2 / 100 - 1)) * s2
        print("%-16s %7.2f %7.2f   %6.1f deg / %5.1f      %6.1f deg / %5.1f      %d of %d"
              % (name + " " + label, max(values), cap, h1, c1, h2, c2, clamped, len(values)))

# spike: does the relative cap still do its job?
ref, sam = load("NowSBudget")
a = absorbance(ref, sam)
spiked = dict(a.valuesByNanometers)
for nm in list(spiked)[:5]:
    spiked[nm] = 40.0
clean = util.spectrumToHsl(a, converter="srgb", ceiling=util.RELATIVE)
noCap = util.spectrumToHsl(spec(spiked), converter="srgb", ceiling=None)
capped = util.spectrumToHsl(spec(spiked), converter="srgb", ceiling=util.RELATIVE)
print("\nT->0 spike (5 bins at A=40): clean hue %.1f | uncapped %.1f (%+.1f) | RELATIVE-capped %.1f (%+.1f)"
      % (clean[0], noCap[0], noCap[0] - clean[0], capped[0], capped[0] - clean[0]))
