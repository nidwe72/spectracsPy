from PySide6.QtGui import qGray

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.playground.PlaygroundCalibrationLogicModule import PlaygroundCalibrationLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import ImageSpectrumAcquisitionLogicModuleParameters
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal
from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType


class SpectralWorkflowEngine:
    # Host engine (SPEC_pumpkin_integration.md C.1). Builds the fixed 5-phase spine, runs the bound
    # plugin's per-phase hooks in order, auto-skips a phase whose hook created 0 steps, and — for the
    # interactive ACQUISITION phase — fills each declared measurement step by capturing from the virtual
    # device through the REAL reader (headless seam: calls ImageSpectrumAcquisitionLogicModule directly,
    # NOT the Qt VideoThread which would deadlock without an event loop — X2).

    PHASE_ORDER = [
        SpectralWorkflowPhaseType.ACQUISITION,
        SpectralWorkflowPhaseType.PROCESSING,
        SpectralWorkflowPhaseType.EVALUATION,
        SpectralWorkflowPhaseType.METADATA,
        SpectralWorkflowPhaseType.PUBLISHING,
    ]

    def __init__(self, plugin):
        self.plugin = plugin
        self.workflow = self.__buildWorkflow()

    @staticmethod
    def resolvePluginFromSession():
        # C.0/D3: import the plugin the logged-in user is bound to. Login resolved the binding to a codeRef
        # (the client can't query the server DB), carried on CurrentUserSession.
        codeRef = CurrentUserSession().getPluginCodeRef()
        return SpectralWorkflowEngine.importPlugin(codeRef)

    @staticmethod
    def importPlugin(codeRef: str):
        # codeRef = "package.module.ClassName" -> import, SDK-compat check, instantiate. The PluginRegistry
        # is the single owner of this (A1); this stays as a thin delegator so existing callers are unchanged.
        from sciens.spectracs.logic.spectral.plugin.PluginRegistry import PluginRegistry
        return PluginRegistry.resolve(codeRef)

    def __buildWorkflow(self) -> SpectralWorkflow:
        workflow = SpectralWorkflow()
        for phaseType in self.PHASE_ORDER:
            phase = SpectralWorkflowPhase()
            phase.setType(phaseType)
            workflow.addToPhases(phase)
        return workflow

    def getWorkflow(self) -> SpectralWorkflow:
        return self.workflow

    def __hookFor(self, phaseType):
        return {
            SpectralWorkflowPhaseType.ACQUISITION: self.plugin.acquisition,
            SpectralWorkflowPhaseType.PROCESSING: self.plugin.processing,
            SpectralWorkflowPhaseType.EVALUATION: self.plugin.evaluation,
            SpectralWorkflowPhaseType.METADATA: self.plugin.metadata,
            SpectralWorkflowPhaseType.PUBLISHING: self.plugin.publishing,
        }[phaseType]

    def runAll(self):
        # Headless convenience: run every phase in order (the GUI drives one phase per Next instead).
        for phaseType in self.PHASE_ORDER:
            self.runPhase(phaseType)
        return self.workflow

    def runPhaseHook(self, phaseType):
        # Run only the plugin hook (declare/compute steps). Interactive ACQUISITION capture is a SEPARATE
        # step so the GUI can trigger it on a Measure click; headless runPhase/runAll capture immediately.
        self.__hookFor(phaseType)(self.workflow)
        return self.workflow.getPhase(phaseType)

    def runPhase(self, phaseType):
        phase = self.runPhaseHook(phaseType)
        if phaseType == SpectralWorkflowPhaseType.ACQUISITION:
            self.__fillAcquisitionSteps(phase)
        return phase

    def isSkipped(self, phaseType) -> bool:
        # A phase whose hook created no steps is auto-skipped (no tab, no stop — §9.1).
        return len(self.workflow.getPhase(phaseType).getSteps()) == 0

    def captureAcquisitionStep(self, step, frameProvider=None, frames=None, onFrame=None):
        # Capture one interactive measurement step — the Measure-button action. The frame SOURCE is a
        # host-injected provider (SPEC_plugin_driven_convergence.md §9.1): a no-arg callable returning the
        # next frame image (or None to skip a dropped frame). Default = the virtual static-image provider
        # (headless, no camera). A real host (bench / wizard on a live device) passes a provider that pumps
        # its own camera thread — so the engine runs the SAME numeric burst without ever touching Qt / camera
        # machinery (stays headless).
        #
        # Capture-context (§9.3, S2b): `frames` overrides the step's frame count (the bench's Frames combo);
        # `onFrame(spectrum, index, total)` is called after each extracted frame so the host can live-plot the
        # running mean + step a progress bar (what the bench's in-view burst did per frame). Both optional.
        # Returns the accumulated spectrum, or None if no frame was delivered (host surfaces "Capture failed").
        self.__ensureCalibration()
        role = step.getRole()
        if role is None:
            return None
        frameCount = frames if frames is not None else (step.getFrames() or 1)
        provider = frameProvider if frameProvider is not None else self.__virtualFrameProvider(role)
        spectrum = self.__runBurst(frameCount, provider, onFrame)
        if spectrum is None:
            return None
        container = SpectraContainer()
        container.addToSpectra(spectrum, role)
        step.setContainer(container)
        return spectrum

    def __fillAcquisitionSteps(self, phase):
        for step in phase.getSteps().values():
            if step.getRole() is not None:
                self.captureAcquisitionStep(step)

    def __ensureCalibration(self):
        # Self-sufficient: if there's no active calibration polynomial, auto-calibrate from the loaded
        # CALIBRATION image (same heuristic as the playground) and install it — so "load the folder" is all
        # the user does; no separate calibration step. (SPEC_pumpkin_integration.md — closes the live gap.)
        applicationSettings = ApplicationContextLogicModule().getApplicationSettings()
        profile = applicationSettings.getSpectrometerProfile()
        calibration = profile.spectrometerCalibrationProfile if profile is not None else None
        hasPolynomial = calibration is not None and getattr(calibration, "interpolationCoefficientA", None) is not None

        calibrationImage = applicationSettings.getVirtualSpectrometerSettings().getImage(VirtualCaptureRole.CALIBRATION)

        # Trust an installed polynomial ONLY when its ROI still lands on signal in the CURRENT calibration
        # image. A profile tuned for a different capture (e.g. an older, differently-sized virtual set) would
        # otherwise sample a black row -> empty spectrum -> no peaks. With no virtual calibration image (a real
        # device) there's nothing to re-detect against, so the stored profile stands.
        if hasPolynomial and (calibrationImage is None or self.__calibrationRoiHasSignal(calibration, calibrationImage)):
            return  # already calibrated and the ROI fits the loaded image

        if calibrationImage is None:
            return  # nothing to (re)calibrate from — capture will surface the missing setup
        calibrationProfile = PlaygroundCalibrationLogicModule().calibrateImage(calibrationImage)
        for attribute in ("regionOfInterestX1", "regionOfInterestX2",
                          "regionOfInterestY1", "regionOfInterestY2"):
            setattr(calibrationProfile, attribute, int(getattr(calibrationProfile, attribute)))
        spectrometerProfile = SpectrometerProfile()
        spectrometerProfile.spectrometerCalibrationProfile = calibrationProfile
        applicationSettings.setSpectrometerProfile(spectrometerProfile)

    def __calibrationRoiHasSignal(self, calibration, image):
        # The reader samples the ROI centre row y=(Y1+Y2)/2 across [X1,X2]; the ROI is only valid for this
        # image if that row actually has lit pixels (same gray>20 threshold the vertical-edge scan uses).
        # An out-of-bounds or all-black row means the profile was tuned for a different capture -> re-detect.
        x1, x2 = calibration.regionOfInterestX1, calibration.regionOfInterestX2
        y1, y2 = calibration.regionOfInterestY1, calibration.regionOfInterestY2
        if None in (x1, x2, y1, y2):
            return False
        centreY = int(y1 + (y2 - y1) / 2.0)
        if not (0 <= centreY < image.height()):
            return False
        left = max(0, min(int(x1), int(x2)))
        right = min(image.width(), max(int(x1), int(x2)))
        for x in range(left, right):
            if qGray(image.pixel(x, centreY)) > 20:
                return True
        return False

    def __virtualFrameProvider(self, role):
        # Default frame source (headless): the active role's virtual image, returned identically each frame
        # (the mean step reduces them). Sets the active role as a side effect, exactly as the old __capture.
        virtualSettings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        virtualSettings.setActiveRole(role)
        image = virtualSettings.getImage(role)
        return lambda: image

    def __runBurst(self, frames, frameProvider, onFrame=None):
        # The numeric burst (Qt-free): pull `frames` frames from the provider and accumulate them into one
        # Spectrum via the REAL reader. `frameProvider` is a no-arg callable returning a frame image (or None
        # for a dropped frame, which is skipped). Reader pulls its calibration from the app-context singleton.
        # This is the ONLY thing that "moved into the engine"; the live camera stays behind the provider
        # (§9.1). `onFrame(spectrum, index, total)` lets the host live-plot / step a progress bar per frame.
        spectrum = None
        for index in range(frames):
            image = frameProvider()
            if image is None:
                continue
            signal = SpectralVideoThreadSignal()
            signal.image = image
            parameters = ImageSpectrumAcquisitionLogicModuleParameters()
            parameters.setVideoSignal(signal)
            parameters.spectrum = spectrum
            spectrum = ImageSpectrumAcquisitionLogicModule().execute(parameters).spectrum
            if onFrame is not None:
                onFrame(spectrum, index, frames)
        return spectrum
