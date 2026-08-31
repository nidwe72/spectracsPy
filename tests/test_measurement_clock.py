"""The measurement clock — `SpectralWorkflow.timestampIso` (SpectralWorkflowEngine.__beginsNewMeasurement).

The bug this pins: the bench builds one engine per VIEW OPENING, not per run, so two measurements made
without leaving the view shared a single construction-time stamp. `20260831SparSBudgetA/001.pdf` and
`/002.pdf` both carry `2026-08-31T16:36:53`, identical to the second, though they were written 5 minutes
apart — the archive could not put the session's own two runs in order.

Drives the REAL engine over the virtual device (no GUI, no Qt event loop), same seam as
test_pumpkin_workflow_end_to_end.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_measurement_clock.py -q
"""
import unittest

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.playground.PlaygroundCalibrationLogicModule import PlaygroundCalibrationLogicModule
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModule import LedReferenceSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModuleParameters import LedReferenceSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModule import OilSampleSynthesisLogicModule
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModuleParameters import OilSampleSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.PlaygroundDemoOils import PLAYGROUND_DEMO_OILS
from sciens.spectracs.logic.spectral.synthesis.SpectrumToVirtualImageUtil import SpectrumToVirtualImageUtil
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.plugins.pumpkin.PumpkinOilPlugin import PumpkinOilPlugin


class MeasurementClockTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        calibration = PlaygroundCalibrationLogicModule().calibrate()
        profile = calibration.profile
        for attribute in ("regionOfInterestX1", "regionOfInterestX2",
                          "regionOfInterestY1", "regionOfInterestY2"):
            setattr(profile, attribute, int(getattr(profile, attribute)))
        spectrometerProfile = SpectrometerProfile()
        spectrometerProfile.spectrometerCalibrationProfile = profile
        ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(spectrometerProfile)

        reference = LedReferenceSynthesisLogicModule().synthesize(
            LedReferenceSynthesisLogicModuleParameters()).getSpectrum()
        parameters = OilSampleSynthesisLogicModuleParameters()
        parameters.setReference(reference)
        parameters.setTargetHue(PLAYGROUND_DEMO_OILS[0].targetHue)
        sample = OilSampleSynthesisLogicModule().synthesize(parameters).getSpectrum()

        imageReference, imageSample = SpectrumToVirtualImageUtil().encode(
            reference, sample, profile, calibration.imageWidth, calibration.imageHeight)
        settings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        settings.setImage(VirtualCaptureRole.REFERENCE, imageReference)
        settings.setImage(VirtualCaptureRole.SAMPLE, imageSample)

    def __engine(self):
        engine = SpectralWorkflowEngine(PumpkinOilPlugin())
        engine.runPhaseHook(SpectralWorkflowPhaseType.ACQUISITION)
        return engine

    @staticmethod
    def __steps(engine):
        phase = engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        return [step for step in phase.getSteps().values() if step.getRole() is not None]

    def __capture(self, engine, step, at):
        # The clock is read inside captureAcquisitionStep, so the fake `now` has to be installed there.
        import sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine as module

        class FrozenDateTime(module.datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return module.datetime.datetime.fromisoformat(at)

        real = module.datetime.datetime
        module.datetime.datetime = FrozenDateTime
        try:
            self.assertIsNotNone(engine.captureAcquisitionStep(step))
        finally:
            module.datetime.datetime = real

    def test_the_reference_leg_stamps_and_the_sample_leg_holds_it(self):
        # ⭐ The field keeps the meaning it was introduced with: when the measurement STARTED. A two-leg run
        # is ONE measurement, so the sample capture must not push the clock forward.
        engine = self.__engine()
        reference, sample = self.__steps(engine)
        self.__capture(engine, reference, "2026-08-31T17:00:00")
        self.assertEqual("2026-08-31T17:00:00", engine.getWorkflow().timestampIso)
        self.__capture(engine, sample, "2026-08-31T17:03:20")
        self.assertEqual("2026-08-31T17:00:00", engine.getWorkflow().timestampIso)

    def test_construction_time_never_reaches_a_captured_run(self):
        # The 20260831SparSBudgetA defect: the stamp was the view-open time, minutes before any capture.
        engine = self.__engine()
        atConstruction = engine.getWorkflow().timestampIso
        self.assertIsNotNone(atConstruction)      # a workflow that never captures still carries a date
        self.__capture(engine, self.__steps(engine)[0], "2026-08-31T17:00:00")
        self.assertNotEqual(atConstruction, engine.getWorkflow().timestampIso)

    def test_a_second_measurement_in_the_same_workflow_gets_its_own_clock(self):
        # ⛔⛔ THE REGRESSION ITSELF. The bench builds no new engine between runs, so this is exactly what
        # 001.pdf and 002.pdf did on 2026-08-31 — and they came out with the same stamp.
        engine = self.__engine()
        reference, sample = self.__steps(engine)
        self.__capture(engine, reference, "2026-08-31T17:00:00")
        self.__capture(engine, sample, "2026-08-31T17:03:20")
        first = engine.getWorkflow().timestampIso

        self.__capture(engine, reference, "2026-08-31T17:09:00")
        self.assertEqual("2026-08-31T17:09:00", engine.getWorkflow().timestampIso)
        self.__capture(engine, sample, "2026-08-31T17:12:40")
        self.assertEqual("2026-08-31T17:09:00", engine.getWorkflow().timestampIso)
        self.assertNotEqual(first, engine.getWorkflow().timestampIso)

    def test_re_reading_the_sample_alone_is_a_new_measurement(self):
        # A fresh sample on a reference that still stands is a new read, and dates as one.
        engine = self.__engine()
        reference, sample = self.__steps(engine)
        self.__capture(engine, reference, "2026-08-31T17:00:00")
        self.__capture(engine, sample, "2026-08-31T17:03:20")
        self.__capture(engine, sample, "2026-08-31T17:20:00")
        self.assertEqual("2026-08-31T17:20:00", engine.getWorkflow().timestampIso)

    def test_a_failed_capture_leaves_the_clock_on_the_data_that_is_there(self):
        # __runBurst returns None when no frame arrives. Nothing entered the workflow, so nothing may move.
        engine = self.__engine()
        reference, sample = self.__steps(engine)
        self.__capture(engine, reference, "2026-08-31T17:00:00")
        self.__capture(engine, sample, "2026-08-31T17:03:20")
        self.assertIsNone(engine.captureAcquisitionStep(reference, frameProvider=lambda: None))
        self.assertEqual("2026-08-31T17:00:00", engine.getWorkflow().timestampIso)

    def test_runAll_dates_the_run_from_its_first_capture(self):
        # The headless path (__fillAcquisitionSteps) captures both legs back to back; one measurement, one clock.
        # ⚠ The fake clock ADVANCES a minute per reading, so "the first capture" is a claim with a witness:
        # construction reads 17:00, the reference 17:01, the sample 17:02, and only one of those may survive.
        import sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine as module
        readings = []

        class TickingDateTime(module.datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                readings.append(len(readings))
                return module.datetime.datetime(2026, 8, 31, 17, len(readings) - 1, 0)

        real = module.datetime.datetime
        module.datetime.datetime = TickingDateTime
        try:
            engine = SpectralWorkflowEngine(PumpkinOilPlugin())
            engine.runAll()
        finally:
            module.datetime.datetime = real
        self.assertGreaterEqual(len(readings), 3)              # construction + both legs really were clocked
        self.assertEqual("2026-08-31T17:01:00", engine.getWorkflow().timestampIso)

    # --- the MONITORED sample leg (captureMonitoredStep) — the path the rig actually takes ---

    def __monitor(self, settles):
        from sciens.spectracs.plugin_sdk import FrameRing, MonitorDecision, MonitorEngine, MonitorOutcome, MonitorPolicy

        class Evaluator:
            version = "clock-test-1"
            valueKey = "widget"
            columns = [{"key": "widget", "label": "Widget", "unit": ""}]

            def evaluate(self, spectrum):
                return {"widget": 1.0}

            def decide(self, rows):
                if not settles:
                    return MonitorDecision.carryOn()
                return MonitorDecision(promote=True, stop=True, outcome=MonitorOutcome.SETTLED_IMMEDIATE,
                                       branch="arrived-clear", readAs="FIRST_SETTLED_WINDOW")

        policy = MonitorPolicy(windowFrames=2, maxSeconds=5.0, maxFrames=8)
        return MonitorEngine(Evaluator(), FrameRing(2, 4), policy)

    def __captureMonitored(self, engine, step, at, settles=True):
        import sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine as module
        settings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        image = settings.getImage(step.getRole())
        ticks = iter(range(1000, 1100))

        class FrozenDateTime(module.datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return module.datetime.datetime.fromisoformat(at)

        real = module.datetime.datetime
        module.datetime.datetime = FrozenDateTime
        try:
            return engine.captureMonitoredStep(step, frameProvider=lambda: image,
                                               monitor=self.__monitor(settles), clock=lambda: next(ticks))
        finally:
            module.datetime.datetime = real

    def test_the_monitored_sample_leg_holds_the_reference_stamp(self):
        # ⭐ The 2026-08-31 runs took THIS path for the sample. One measurement, dated from where it began.
        engine = self.__engine()
        reference, sample = self.__steps(engine)
        self.__capture(engine, reference, "2026-08-31T17:00:00")
        result = self.__captureMonitored(engine, sample, "2026-08-31T17:03:20")
        self.assertTrue(result.hasValue())
        self.assertIsNotNone(sample.getContainer())
        self.assertEqual("2026-08-31T17:00:00", engine.getWorkflow().timestampIso)

    def test_a_monitored_re_read_of_the_sample_gets_its_own_clock(self):
        engine = self.__engine()
        reference, sample = self.__steps(engine)
        self.__capture(engine, reference, "2026-08-31T17:00:00")
        self.__captureMonitored(engine, sample, "2026-08-31T17:03:20")
        self.__captureMonitored(engine, sample, "2026-08-31T17:09:00")
        self.assertEqual("2026-08-31T17:09:00", engine.getWorkflow().timestampIso)

    def test_a_monitored_run_that_answers_nothing_does_not_move_the_clock(self):
        # ⛔ CapturePanel.__onMonitorFinished takes the container back off such a run, so the clock must not
        # have followed it: the workflow still holds the earlier measurement's data, dated from its reference.
        engine = self.__engine()
        reference, sample = self.__steps(engine)
        self.__capture(engine, reference, "2026-08-31T17:00:00")
        self.__captureMonitored(engine, sample, "2026-08-31T17:03:20")
        result = self.__captureMonitored(engine, sample, "2026-08-31T17:09:00", settles=False)
        self.assertFalse(result.hasValue())
        self.assertEqual("2026-08-31T17:00:00", engine.getWorkflow().timestampIso)


if __name__ == "__main__":
    unittest.main()
