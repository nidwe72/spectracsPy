from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer


class EvaluationResultRenderer:
    # Thin façade kept for existing call sites (SPEC_pumpkin_integration.md C.3). The actual rendering now runs
    # through the shared visitor seam (SPEC_plugin_driven_convergence.md §2A / P1): the plugin's Qt-free
    # EvaluationResult view-models → QWidget via QtWorkflowRenderer, so the same dispatch serves the matplotlib
    # report target (M2). Behaviour is identical to the previous inline renderer.

    def render(self, evaluationResult):
        return QtWorkflowRenderer().render(evaluationResult.getItems())
