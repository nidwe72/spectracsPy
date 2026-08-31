import datetime

from PySide6.QtGui import qGray

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.playground.PlaygroundCalibrationLogicModule import PlaygroundCalibrationLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import ImageSpectrumAcquisitionLogicModuleParameters
from sciens.spectracs.logic.spectral.acquisition.CaptureDiagnosticsLogger import CaptureDiagnosticsLogger
from sciens.spectracs.logic.spectral.workflow.PrepProtocolResolver import PrepProtocolResolver
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.model.spectral.plugin.view.EvaluationResult import EvaluationResult
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
        # Step ids captured since the clock was last stamped — the ONLY state the measurement clock needs.
        # See `__beginsNewMeasurement`.
        self.__capturedSinceStamp = set()
        self.workflow = self.__buildWorkflow()

    @staticmethod
    def resolvePluginFromSession():
        # C.0/D3: import the plugin the logged-in user is bound to. Login resolved the binding to
        # (codeRef, version) (the client can't query the server DB), carried on CurrentUserSession (B5.4).
        session = CurrentUserSession()
        return SpectralWorkflowEngine.importPlugin(session.getPluginCodeRef(), session.getPluginVersion())

    @staticmethod
    def importPlugin(codeRef: str, version: str = None):
        # (codeRef, version) -> resolve. PluginRegistry is the single owner (A1); resolve routes built-in vs
        # DB on the row's sealedness (B6.4). version=None -> the shipped built-in (no server fetch).
        from sciens.spectracs.logic.spectral.plugin.PluginRegistry import PluginRegistry
        return PluginRegistry.resolve(codeRef, version)

    def __buildWorkflow(self) -> SpectralWorkflow:
        workflow = SpectralWorkflow()
        # ⭐ The PLUGIN declares what it is measuring in; the workflow only carries it to the report.
        solvent = getattr(self.plugin, "solvent", None)
        workflow.solvent = getattr(solvent, "value", None) or "UNKNOWN"
        # ⛔ RESOLVED PER RUN, not read off the class. See PrepProtocolResolver: the compiled-in constant
        # went stale twice and cost the archive its whole pre-vortex population (§16.15).
        workflow.prepProtocol = PrepProtocolResolver.resolve(getattr(self.plugin, "prepProtocol", None))
        # ⛔ THIS IS THE FALLBACK, NOT THE MEASUREMENT CLOCK. It runs at ENGINE CONSTRUCTION, which the
        # bench does on `showEvent` — i.e. when the view is opened, before the operator has filled anything.
        # `captureAcquisitionStep` overwrites it with the time capture actually began; this value survives only
        # for a workflow that never captured, where a stamp is still better than the `timestampIso: null` that
        # §16.23.2b step 8 ("log the temperature WITH THE CLOCK TIME") had no clock to log against.
        # ⚠ Kept for the same reason it was introduced: a run exported to PDF without being saved must not
        # reach the archive undated. `AbstractPluginExecutionView._persistNewRun` stamps only if this is unset.
        workflow.timestampIso = datetime.datetime.now().isoformat(timespec="seconds")
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
        commitClock = self.__openMeasurementClock(step)
        frameCount = frames if frames is not None else (step.getFrames() or 1)
        provider = frameProvider if frameProvider is not None else self.__virtualFrameProvider(role)
        spectrum = self.__runBurst(frameCount, provider, onFrame)
        if spectrum is None:
            return None
        commitClock()
        # Env-gated diagnostic (SPEC_capability_proof.md §7.0.1): dump per-frame spectra + the C1 rejection mask +
        # brightness for the reference gray-outlier investigation. No-op unless SPECTRACS_LOG_SPECTRA is set.
        CaptureDiagnosticsLogger().log(role, spectrum)
        container = SpectraContainer()
        container.addToSpectra(spectrum, role)
        step.setContainer(container)
        return spectrum

    def __openMeasurementClock(self, step):
        """Read the measurement clock BEFORE a capture; returns the `commit` that writes it AFTER.

        ⭐⭐ BEFORE, because the sample leg carries the settling monitor: it ran 173 s and 230 s on the two
        2026-08-31 runs and its policy allows 1500 s, so a stamp taken afterwards would date the measurement
        by up to 25 minutes late — which is the same class of error this whole rule exists to remove.

        ⛔ COMMITTED ONLY WHEN THE CAPTURE DELIVERED. Both capture paths can return without putting a
        container on the step (no frame from the provider; a monitor that produced no spectrum). Nothing
        entered the workflow, so the clock must stay on the data that is still in it.

        ⛔ Both paths share this ONE pair. `captureMonitoredStep` is not a variant of the burst — it is the
        path the rig's SAMPLE leg actually takes — and a rule applied to only one of them would date the
        reference and leave the measurement itself unaccounted for.

        ⚠ KNOWN GAP, deliberately not closed here: a host CAN discard a container after the engine set it.
        `CapturePanel` does exactly that on a cancelled capture (§12.1) — a host-side concept the engine is
        not told about — so a cancelled re-read of the sample alone leaves the clock on the abandoned
        attempt. It cannot reach a report: the step has no container, `__acquisitionComplete()` is false,
        and the run cannot advance out of ACQUISITION. Closing it properly means the host discarding
        THROUGH the engine rather than through `setContainer(None)`, which is a wider change than dating
        a run is worth.
        """
        beganAt = datetime.datetime.now().isoformat(timespec="seconds")
        newMeasurement = self.__beginsNewMeasurement(step)

        def commit():
            if newMeasurement:
                self.workflow.timestampIso = beganAt
                self.__capturedSinceStamp = set()
            self.__capturedSinceStamp.add(step.getId())
        return commit

    def __beginsNewMeasurement(self, step) -> bool:
        """Whether capturing `step` starts a NEW measurement, and so re-stamps `workflow.timestampIso`.

        ⛔⛔ THE BENCH RESTARTS NOTHING BETWEEN RUNS. `DevMeasurementBenchViewModule.__enterRun` — the only
        caller of `_startNewRun`, and so the only thing that builds a fresh engine — fires on `showEvent` and
        on a plugin change, nothing else. Going back to ACQUISITION and measuring again reuses this workflow,
        so before this rule the archive's 20260831SparSBudgetA/001.pdf and /002.pdf both read
        `timestampIso: 2026-08-31T16:36:53` — identical to the second, though the two PDFs were written 5
        minutes apart and their monitors ran 173 s and 230 s. Two runs of one session could not be ordered.

        The rule is that a capture begins a new measurement when it REPEATS a step already captured under the
        current stamp, or when nothing has been captured at all:

          * reference then sample, first time  -> stamps on the reference, holds through the sample, so the
            field keeps the meaning it was introduced with: when the measurement STARTED, not when it ended
            and not when it was filed;
          * reference again (a re-measure)     -> re-stamps, and the sample that follows holds that stamp;
          * sample alone, reference kept       -> re-stamps, which is right: it is a new read.

        ⚠ The "nothing captured" test reads the CONTAINERS, not `__capturedSinceStamp`. A re-run phase hook
        rebuilds the steps with new uuids and drops their containers; that is genuinely a fresh measurement,
        and a set of now-unreachable ids would have said otherwise.
        """
        phase = self.workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        captured = any(candidate.getContainer() is not None
                       for candidate in phase.getSteps().values() if candidate.getRole() is not None)
        return (not captured) or step.getId() in self.__capturedSinceStamp

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
        # The numeric burst (Qt-free): pull frames from the provider and accumulate them into one Spectrum via
        # the REAL reader. `frameProvider` is a no-arg callable returning a frame image (or None for a dropped
        # frame, which is skipped). Reader pulls its calibration from the app-context singleton. The live camera
        # stays behind the provider (§9.1). `onFrame(spectrum, index, total)` lets the host live-plot / step a
        # progress bar per frame.
        #
        # C3 (SPEC_capture_quality.md §14.8): GRAB UNTIL `frames` frames SURVIVE per-frame brightness rejection,
        # so the EFFECTIVE count feeding the mean is the intended N even when a few dim/spike frames get dropped
        # by C1. Bounded: at most `frames + margin` accepted, and a total-attempt cap so a provider that keeps
        # returning None (a wedged camera) fails cleanly instead of looping forever.
        target = frames
        maxFrames = target + max(5, target // 5)     # +20% (or +5) headroom to replace rejected frames
        # ⭐ TERMINATION IS A SAFETY PROPERTY, NOT A FEATURE (SPEC_settled_measurement.md §12.2): an
        # acquisition that can fail to terminate is an instrument that can hang with the lamp on the
        # sample. `maxAttempts` already bounds a provider that keeps returning None — which is also the
        # path a CANCEL takes (§12.1a: the panel's provider returns None once the flag is set), so a
        # cancelled burst unwinds through machinery that was always here.
        maxAttempts = maxFrames + target             # also bound provider None-returns (dropped/dead/CANCELLED)
        spectrum = None
        captured = 0
        attempts = 0
        while captured < maxFrames and attempts < maxAttempts:
            attempts += 1
            image = frameProvider()
            if image is None:
                continue
            signal = SpectralVideoThreadSignal()
            signal.image = image
            parameters = ImageSpectrumAcquisitionLogicModuleParameters()
            parameters.setVideoSignal(signal)
            parameters.spectrum = spectrum
            spectrum = ImageSpectrumAcquisitionLogicModule().execute(parameters).spectrum
            captured += 1
            if onFrame is not None:
                onFrame(spectrum, min(captured, target) - 1, target)   # progress fills to N, then top-up is silent
            if captured >= target and self.__survivingFrameCount(spectrum) >= target:
                break
        return spectrum

    def captureMonitoredStep(self, step, frameProvider, monitor, onRow=None, clock=None):
        """The MONITORED sibling of captureAcquisitionStep (SPEC_settled_measurement.md §10.4).

        ⭐ THIN BY DESIGN: it pumps the provider, hands each frame to the monitor the PLUGIN built, and
        returns that monitor's result. ⛔ The algorithm is NOT here — this module imports Qt (`qGray`),
        and the monitor must stay Qt-free per SPEC_project_structure.md. Nothing in this method knows what
        settling, turbidity or `Q%` are.

        ⚠ `clock` is injected and defaults to `time.monotonic` (§25/X3): wall-clock can step backwards
        during a 20-minute run, which would make a rate negative and a re-clouding reset fire on nothing.
        ⚠ The host owns the no-frame watchdog (§12.2/L3) — the engine only learns that time passed when
        someone offers a frame, so a wedged camera cannot wake an engine-side timer.
        """
        import time
        self.__ensureCalibration()
        commitClock = self.__openMeasurementClock(step)
        clock = clock or time.monotonic
        attempts = 0
        maxAttempts = monitor.policy.maxFrames * 2
        while not monitor.isFinished() and attempts < maxAttempts:
            attempts += 1
            image = frameProvider()
            if image is None:
                continue
            frame = self.__frameSpectrum(image)
            if frame is None:
                continue
            row = monitor.offer(frame, clock())
            if row is not None and onRow is not None:
                onRow(row, monitor)
        result = monitor.result()
        spectrum = result.spectrum
        if spectrum is None and result.hasValue():
            # ⛔⛔ A RUN THAT PRODUCED AN ANSWER IS NEVER THROWN AWAY (SPEC_settled_measurement.md §27.25/M3).
            # This is the last line of defence, not the fix: §27.25/M1 makes the winning row's spectrum
            # survive for the whole run, so this branch should now be unreachable. It exists because the
            # failure it guards was SILENT and expensive — the operator was told "no frames were delivered
            # by the camera" about a run in which every frame arrived and the gate fired, and the natural
            # response (re-measure the same jar) banked light dose and biased the repeat upward.
            # ⇒ fall back to the newest decision row that still HAS a spectrum, and say so out loud.
            fallback = next((row for row in reversed(result.decisionRows())
                             if getattr(row, "spectrum", None) is not None), None)
            spectrum = getattr(fallback, "spectrum", None)
            print("MONITOR ⚠ the answer's own spectrum was missing (answer t=%.1fs); %s"
                  % (result.answer.get("t", float("nan")),
                     "fell back to the row at t=%.1fs" % fallback.t if fallback is not None
                     else "NO row retained one — the measurement cannot be completed"))
            result.notes.append("the answer's spectrum was missing; %s"
                                % ("read from the nearest retained row" if fallback is not None
                                   else "no spectrum could be recovered"))
        if spectrum is not None:
            container = SpectraContainer()
            container.addToSpectra(spectrum, step.getRole())
            step.setContainer(container)
            # ⚠ `hasValue`, not just a spectrum. A monitored run can carry frames and still answer nothing
            # (NEVER_SETTLED / MEASUREMENT_BROKEN / STALLED), and `CapturePanel.__onMonitorFinished` then
            # takes the container straight back off — so committing on the spectrum alone would leave the
            # clock on an attempt that put no data in the workflow.
            if result.hasValue():
                commitClock()
        self.__attachMonitorViews(step, result)
        return result

    def __attachMonitorViews(self, step, result):
        """Hang the plugin's views for this run on the step they DESCRIBE (SPEC_settled_measurement.md §27.12).

        ⭐⭐ ONE CONSTRUCTION, ONE HOME. The settling curves are provenance of THIS capture, so they live on
        this acquisition step's EvaluationResult — where the report already harvests (it pulls the raster
        and spectrum views off exactly the same place) and where persistence already round-trips them.
        ⇒ the capture panel renders these very objects, the PDF collects these very objects, and the
        report files them under **Acquisition**, which is where they happened.

        ⛔ What this replaced: the plugin declared a second, report-only step in PROCESSING while the panel
        separately built the same views again from the same record — the same thing constructed twice into
        two homes, with a persisted flag invented to stop one of them showing up.
        ⚠ Invisible in the UI by construction: `WorkflowPhaseRenderer.renderStep()` sends a CaptureView
        step to the capture path, which never looks at its EvaluationResult.
        """
        plugin = getattr(self, "plugin", None)
        if plugin is None or not hasattr(plugin, "settlingView"):
            return
        try:
            view = plugin.settlingView(result.toRecord())
        except Exception as error:            # a diagnostic must never break the capture it documents
            print("SETTLING views unavailable (%s)" % error)
            return
        if view is None:
            return
        evaluationResult = step.getEvaluationResult()
        if evaluationResult is None:
            evaluationResult = EvaluationResult()
            step.setEvaluationResult(evaluationResult)
        # ⚠ Re-measuring the same role must REPLACE, not accumulate: a second run's curve beside the
        # first's would put two contradictory provenances on one capture.
        for existing in [item for item in evaluationResult.getItems() if getattr(item, "isMonitorView", False)]:
            evaluationResult.getItems().remove(existing)
        view.isMonitorView = True
        evaluationResult.addItem(view)
        result.views = [view]

    def __frameSpectrum(self, image):
        # ONE frame -> {nm: value}, through the app's OWN per-frame extraction — the same module the burst
        # path uses, so a monitored row and a bench capture are reduced identically (§10.7b).
        signal = SpectralVideoThreadSignal()
        signal.image = image
        parameters = ImageSpectrumAcquisitionLogicModuleParameters()
        parameters.setVideoSignal(signal)
        parameters.spectrum = None
        spectrum = ImageSpectrumAcquisitionLogicModule().execute(parameters).spectrum
        frames = spectrum.getCapturedValuesByNanometers() if spectrum is not None else None
        return frames[-1] if frames else None

    def __survivingFrameCount(self, spectrum):
        # How many captured frames would survive C1's per-frame brightness rejection (the SAME test the final
        # MeanSpectrum reduce applies) — so the top-up loop stops once the mean will see N clean frames.
        import numpy as np
        from sciens.spectracs.logic.spectral.acquisition.RobustReductionLogicModule import RobustReductionLogicModule
        frames = spectrum.getCapturedValuesByNanometers() if spectrum is not None else None
        if not frames:
            return 0
        keys = list(frames[0].keys())
        stack = np.array([[frame.get(key, np.nan) for key in keys] for frame in frames], dtype=float)
        return int(np.sum(RobustReductionLogicModule().rejectDimFrames(stack)))
