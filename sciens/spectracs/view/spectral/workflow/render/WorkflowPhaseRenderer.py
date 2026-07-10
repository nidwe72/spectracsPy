from PySide6.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QLabel

from sciens.spectracs.model.spectral.plugin.view.CaptureView import CaptureView
from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView
from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer


class WorkflowPhaseRenderer:
    # SPEC_plugin_driven_convergence.md §2B/§4 (P3) — the ONE place "steps -> tabs" lives. Renders a
    # WorkflowPhase's steps as a QTabWidget; each tab is a step's content, drawn generically via the shared
    # visitor (QtWorkflowRenderer). Headless steps (no renderable content) get no tab. Both hosts (bench +
    # wizard) delegate per-phase rendering here; they differ only in navigation + the injected chrome/capture.
    #
    # Hooks (host-supplied, both optional):
    #   captureHandler(step, captureView) -> QWidget : builds the interactive capture panel (host owns the camera)
    #   decorateCapturePanel(panel, step)            : dev-chrome extension hook (bench injects exposure/ROI;
    #                                                  wizard leaves it empty)

    def __init__(self, captureHandler=None, decorateCapturePanel=None):
        self.__captureHandler = captureHandler
        self.__decorateCapturePanel = decorateCapturePanel

    def render(self, phase) -> QTabWidget:
        tabs = QTabWidget()
        for step in phase.getSteps().values():
            content = self.renderStep(step)
            if content is not None:
                tabs.addTab(content, step.getLabel() or "")
        return tabs

    def renderStep(self, step):
        # A capture step (CaptureView on _view) → the interactive host capture path; anything else → the passive
        # visitor over the step's view-models. Returns None for a headless step (no content → no tab).
        view = step.getView() if hasattr(step, "getView") else None
        if isinstance(view, CaptureView):
            return self.__renderCapture(step, view)
        items = self.stepViewModels(step)
        if not items:
            return None
        return QtWorkflowRenderer().render(items)

    def stepViewModels(self, step):
        # Adapter (SPEC §4 "generalize step content"): a step's renderable content as a flat view-model list —
        # its EvaluationResult items, then its passive _view (SpectrumPlotView / SpectrumCaptureView).
        items = []
        result = step.getEvaluationResult() if hasattr(step, "getEvaluationResult") else None
        if result is not None:
            items.extend(result.getItems())
        view = step.getView() if hasattr(step, "getView") else None
        # CaptureView (interactive) and ReportView (a report descriptor the generic host can't render) are NOT
        # passive visitor items — skip them. A report-aware host (the dev bench, M2) special-cases the ReportView
        # step before delegating here; in a generic host a report step is simply headless (no tab).
        if view is not None and not isinstance(view, (CaptureView, ReportView)):
            items.append(view)
        return items

    def __renderCapture(self, step, captureView):
        if self.__captureHandler is not None:
            panel = self.__captureHandler(step, captureView)
        else:
            panel = QWidget()
            layout = QVBoxLayout()
            panel.setLayout(layout)
            if captureView.prompt:
                layout.addWidget(QLabel(captureView.prompt))
        if self.__decorateCapturePanel is not None:
            self.__decorateCapturePanel(panel, step)
        return panel
