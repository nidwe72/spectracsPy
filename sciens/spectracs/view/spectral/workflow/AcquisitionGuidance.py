from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPolygon

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal


class AcquisitionGuidance:
    """Host-agnostic acquisition-guidance primitives (SPEC_plugin_driven_convergence.md §9 D4 / S1a).

    The amber ● / ▶ cue icons, the capture-button dot, and the status-bar coach-line emit were mirrored
    byte-for-byte in `WizardViewModule` and `DevMeasurementBenchViewModule`. Lifted here so both hosts share
    ONE implementation. Each host keeps only its nav-specific bits — the acquisition entry gate and the
    highlight targets — which can't unify while the two nav skins stand (D3). No host state, so a host just
    holds one instance and delegates to it.

    The full guidance collapse (derivation + highlight application) is S4a; this is only the byte-identical
    primitives.
    """

    def __init__(self):
        self.__amberDot = None      # lazily-painted amber ● cue icon
        self.__amberArrow = None    # lazily-painted amber ▶ Next-button cue icon

    def amberDotIcon(self):
        if self.__amberDot is None:
            self.__amberDot = self.__paintGuidanceIcon("dot")
        return self.__amberDot

    def amberArrowIcon(self):
        if self.__amberArrow is None:
            self.__amberArrow = self.__paintGuidanceIcon("arrow")
        return self.__amberArrow

    def setButtonDot(self, button, on):
        # ⛔ NEVER while that button says "Cancel" (SPEC_settled_measurement.md §12.1a). During a capture
        # the measure button IS the cancel button, and painting the amber "do this next" dot on it urges
        # the operator to press the one control that ABANDONS the measurement.
        # ⚠ Enforced HERE rather than at each call site: the bench and the wizard both paint dots, and the
        # rig showed a "● Cancel" button because only one of the two paths had been guarded.
        if button is not None and on and str(button.text()).startswith(("Cancel", "Cancelling")):
            button.setIcon(QIcon())
            return
        if button is not None:
            button.setIcon(self.amberDotIcon() if on else QIcon())

    def deriveAction(self, steps, completeHint):
        # Shared next-action derivation (S4a): the first still-uncaptured step + its coach text — the plugin's
        # prompt verbatim, else "Press <captureLabel>". All captured -> the phase's completion hint (or None).
        # "measured?" is the workflow model (step.getContainer()), identical for both hosts (D4).
        nextStep = next((step for step in steps if step.getContainer() is None), None)
        if nextStep is not None:
            view = nextStep.getView()
            hint = getattr(view, "prompt", None) if view is not None else None
            if not hint:
                label = getattr(view, "captureLabel", None) if view is not None else None
                hint = "Press %s" % (label or "Capture")
            coach = hint
        else:
            coach = completeHint
        return {"steps": steps, "nextStep": nextStep, "coach": coach}

    def applyPanelHighlights(self, panel, action):
        # Shared amber-cue application for a CapturePanel (S4a): ✓ on captured role-tabs, amber ● on the active
        # capture button or the target role-tab. Identical for the bench and the wizard-real path (D4 keeps the
        # highlight TARGETS host-side — a CapturePanel — but the logic is one place now).
        tabs = panel.getRoleTabs()
        bar = tabs.tabBar()
        steps = action["steps"]
        for index, step in enumerate(steps):
            baseLabel = step.getLabel() or (step.getRole() or "")
            captured = step.getContainer() is not None
            tabs.setTabText(index, ("✓ " + baseLabel) if captured else baseLabel)
            bar.setTabIcon(index, QIcon())
        self.setButtonDot(panel.getCaptureButton(), False)
        nextStep = action["nextStep"]
        if nextStep is None:
            return
        # ⛔ No "do this next" dot on a capture button the lamp gate holds disabled (SPEC_lamp_switch.md §16 U3)
        if not AcquisitionGuidance.lampReady():
            return
        # ⛔ §12.1a: while a capture is running that button says "Cancel". Painting the amber ▶ NEXT cue on
        # it would urge the operator to press the one control that ABANDONS the measurement.
        if getattr(panel, "isCapturing", None) is not None and panel.isCapturing():
            return
        nextIndex = steps.index(nextStep)
        if nextStep is panel.getActiveStep():
            self.setButtonDot(panel.getCaptureButton(), True)
        else:
            bar.setTabIcon(nextIndex, self.amberDotIcon())

    def emit(self, text):
        # Guidance text → muted-amber font, no progress bar. A None/empty text rests the bar instead
        # (equivalent to the hosts' former __emitStatusReset / __clearStatus).
        signal = ApplicationStatusSignal()
        if not text:
            signal.isStatusReset = True
        else:
            signal.isStatusReset = False
            signal.guidance = True
            signal.text = text
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    # --- lamp (SPEC_lamp_switch.md §16.2, G9) ---------------------------------------------------------------

    def emitAcquisition(self, coach):
        """The ACQUISITION coach line, with the lamp's line winning over the plugin's cue. WARMING is one
        determinate bar that IS the coach line (§16 U1) — never a bar and a line fighting over one widget."""
        service = AcquisitionGuidance.__lamp()
        from sciens.spectracs.logic.lamp.LampState import LampState
        if service is not None and service.wantsOn and service.state == LampState.WARMING:
            total = service.warmUpSeconds
            elapsed = max(0, total - service.warmUpRemainingSeconds())
            signal = ApplicationStatusSignal()
            signal.isStatusReset = False
            signal.stepsCount = total
            signal.currentStepIndex = elapsed
            signal.text = "Lamp warming up — 0:%02d of 0:%02d" % (elapsed, total)
            ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)
            return
        self.emit(AcquisitionGuidance.lampCoach(coach))

    @staticmethod
    def lampCoach(coach):
        """Pure text rule of §16.2 (testable without a status bar)."""
        service = AcquisitionGuidance.__lamp()
        if service is None or service.owner is None or not service.wantsOn:
            return coach
        from sciens.spectracs.logic.lamp.LampState import LampState
        state = service.state
        if state == LampState.SEARCHING:
            return "Looking for the lamp plug …"
        if state == LampState.OFF:
            stopped = service.offMessage()
            if stopped:
                return stopped + " Switch the lamp on with the lamp icon to measure again."
            return "The lamp is off — switch it on with the lamp icon."
        if state == LampState.NO_PLUG:
            if service.needsPassword:
                return ("The lamp plug needs a password — switch the lamp on at the socket for now; set the "
                        "password in Settings → Lamp after this measurement.")
            note = "switch the lamp on at the socket, 20 s warm-up"
            return "%s  ·  %s" % (coach, note) if coach else note.capitalize()
        if state == LampState.UNREACHABLE:
            return "The lamp plug is not answering — check the Wi-Fi."
        if state == LampState.ON and service.noPower:
            return "The plug is on but the lamp draws no power — check the switch on the lamp socket."
        return coach

    @staticmethod
    def lampReady():
        service = AcquisitionGuidance.__lamp()
        return service is None or service.readyForCapture()

    @staticmethod
    def __lamp():
        from sciens.spectracs.logic.lamp.LampService import LampService
        return LampService.instance

    def __paintGuidanceIcon(self, shape):
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(ApplicationStyleLogicModule().getGuidanceColor())
        if shape == "arrow":
            painter.drawPolygon(QPolygon([QPoint(3, 2), QPoint(10, 6), QPoint(3, 10)]))  # right-pointing ▶
        else:
            painter.drawEllipse(2, 2, 8, 8)  # ●
        painter.end()
        return QIcon(pixmap)
