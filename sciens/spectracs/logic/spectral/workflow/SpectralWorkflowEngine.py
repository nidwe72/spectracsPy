import importlib

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
        # codeRef = "package.module.ClassName" -> import and instantiate.
        moduleName, className = codeRef.rsplit(".", 1)
        module = importlib.import_module(moduleName)
        return getattr(module, className)()

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

    def captureAcquisitionStep(self, step):
        # Capture one interactive measurement step from the (virtual) device — the Measure-button action.
        self.__ensureCalibration()
        role = step.getRole()
        if role is None:
            return
        frames = step.getFrames() or 1
        spectrum = self.__capture(role, frames)
        container = SpectraContainer()
        container.addToSpectra(spectrum, role)
        step.setContainer(container)

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
        if calibration is not None and getattr(calibration, "interpolationCoefficientA", None) is not None:
            return  # already calibrated

        calibrationImage = applicationSettings.getVirtualSpectrometerSettings().getImage(VirtualCaptureRole.CALIBRATION)
        if calibrationImage is None:
            return  # nothing to calibrate from — capture will surface the missing setup
        calibrationProfile = PlaygroundCalibrationLogicModule().calibrateImage(calibrationImage)
        for attribute in ("regionOfInterestX1", "regionOfInterestX2",
                          "regionOfInterestY1", "regionOfInterestY2"):
            setattr(calibrationProfile, attribute, int(getattr(calibrationProfile, attribute)))
        spectrometerProfile = SpectrometerProfile()
        spectrometerProfile.spectrometerCalibrationProfile = calibrationProfile
        applicationSettings.setSpectrometerProfile(spectrometerProfile)

    def __capture(self, role, frames):
        # Set the active role, then read the virtual image `frames` times into one Spectrum's captured
        # frames (each identical for a virtual device — the mean step reduces them). Reader pulls its
        # calibration from the app-context singleton.
        virtualSettings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        virtualSettings.setActiveRole(role)
        image = virtualSettings.getImage(role)
        spectrum = None
        for _ in range(frames):
            signal = SpectralVideoThreadSignal()
            signal.image = image
            parameters = ImageSpectrumAcquisitionLogicModuleParameters()
            parameters.setVideoSignal(signal)
            parameters.spectrum = spectrum
            spectrum = ImageSpectrumAcquisitionLogicModule().execute(parameters).spectrum
        return spectrum
