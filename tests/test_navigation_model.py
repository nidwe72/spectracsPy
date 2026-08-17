# M1 unit tests for the generic navigation model (SPEC_simplified_plugin_navigation.md §12, milestone M1).
# Pure / Qt-free: builds workflows in memory and asserts NavigationModel.stops(). No host, no engine, no camera.

from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType as P

from sciens.spectracs.plugin_sdk.policy.NavigationMode import NavigationMode
from sciens.spectracs.plugin_sdk.policy.NavigationPolicy import NavigationPolicy
from sciens.spectracs.plugin_sdk.policy.WorkflowPolicy import WorkflowPolicy
from sciens.spectracs.logic.spectral.navigation.NavigationModel import NavigationModel
from sciens.spectracs.logic.spectral.navigation.NavStop import NavStopKind


def _step(label, role=None):
    step = SpectralWorkflowStep()
    step.setLabel(label)
    if role is not None:
        step.setRole(role)
    return step


def _workflow(stepsByPhase):
    # stepsByPhase: {phaseType: [labels]} — build the canonical spine with the given steps.
    workflow = SpectralWorkflow()
    for phaseType in NavigationModel.PHASE_ORDER:
        phase = SpectralWorkflowPhase()
        phase.setType(phaseType)
        workflow.addToPhases(phase)
        for label in stepsByPhase.get(phaseType, []):
            phase.addToSteps(_step(label))
    return workflow


def _labels(stops):
    return [s.label for s in stops]


def _phaseTypes(stops):
    return [s.phaseType for s in stops]


def test_default_policy_one_phase_stop_per_nonempty_phase_in_order():
    wf = _workflow({P.ACQUISITION: ["Reference", "Sample"], P.PROCESSING: ["Spectra"],
                    P.EVALUATION: ["Metrics"]})
    stops = NavigationModel.stops(wf, NavigationPolicy.default())
    assert all(s.kind == NavStopKind.PHASE for s in stops)
    assert _phaseTypes(stops) == [P.ACQUISITION, P.PROCESSING, P.EVALUATION]
    assert _labels(stops) == ["Acquisition", "Processing", "Evaluation"]


def test_empty_phase_is_skipped():
    # No PUBLISHING steps -> no publishing stop; empty PROCESSING dropped too.
    wf = _workflow({P.ACQUISITION: ["Reference"], P.EVALUATION: ["Metrics"]})
    stops = NavigationModel.stops(wf, NavigationPolicy.default())
    assert _phaseTypes(stops) == [P.ACQUISITION, P.EVALUATION]


def test_step_expansion_turns_acquisition_steps_into_chevrons():
    wf = _workflow({P.ACQUISITION: ["Reference", "Sample"], P.PROCESSING: ["Spectra"]})
    policy = NavigationPolicy(NavigationMode.AUTO_ADVANCE, stepChevronPhases={P.ACQUISITION})
    stops = NavigationModel.stops(wf, policy)
    # two STEP stops for ACQUISITION, then a PHASE stop for PROCESSING
    assert [s.kind for s in stops] == [NavStopKind.STEP, NavStopKind.STEP, NavStopKind.PHASE]
    assert _labels(stops) == ["Reference", "Sample", "Processing"]
    assert _phaseTypes(stops) == [P.ACQUISITION, P.ACQUISITION, P.PROCESSING]
    # STEP stops carry their step; PHASE stops do not
    assert stops[0].step is not None and stops[0].isStep()
    assert stops[2].step is None and stops[2].isPhase()


def test_stops_are_mode_independent():
    # STEP vs AUTO_ADVANCE with the SAME expansion set produce the SAME chevron list (only cursor behaviour,
    # i.e. the auto-advance jump, differs — that is not stops()' concern). §9b-21.
    wf = _workflow({P.ACQUISITION: ["Reference", "Sample"], P.PROCESSING: ["Spectra"], P.PUBLISHING: ["LIMS"]})
    stepP = NavigationPolicy(NavigationMode.STEP, stepChevronPhases={P.ACQUISITION})
    autoP = NavigationPolicy(NavigationMode.AUTO_ADVANCE, stepChevronPhases={P.ACQUISITION})
    a = NavigationModel.stops(wf, stepP)
    b = NavigationModel.stops(wf, autoP)
    assert _labels(a) == _labels(b)
    assert [s.kind for s in a] == [s.kind for s in b]


def test_metadata_is_uniform_when_it_has_a_step():
    # Change E: once a metadata step is materialised, METADATA is treated like any other phase (no special case).
    wf = _workflow({P.ACQUISITION: ["Reference"], P.METADATA: ["Details"], P.PUBLISHING: ["LIMS"]})
    stops = NavigationModel.stops(wf, NavigationPolicy.default())
    assert _phaseTypes(stops) == [P.ACQUISITION, P.METADATA, P.PUBLISHING]
    assert all(s.kind == NavStopKind.PHASE for s in stops)


def test_metadata_carveout_appears_when_fields_present_but_no_step():
    # The metadata phase has no engine steps; the host passes hasMetadataFields so its chevron still appears
    # (rendered as a transient form — NOT a persisted step, so saved runs are unchanged).
    wf = _workflow({P.ACQUISITION: ["Reference"], P.EVALUATION: ["Result"]})
    without = NavigationModel.stops(wf, NavigationPolicy.default())
    assert P.METADATA not in _phaseTypes(without)
    with_meta = NavigationModel.stops(wf, NavigationPolicy.default(), hasMetadataFields=True)
    assert _phaseTypes(with_meta) == [P.ACQUISITION, P.EVALUATION, P.METADATA]


def test_none_policy_behaves_as_default():
    wf = _workflow({P.ACQUISITION: ["Reference"], P.PROCESSING: ["Spectra"]})
    assert _labels(NavigationModel.stops(wf, None)) == ["Acquisition", "Processing"]


def test_workflow_policy_container_defaults_to_step_no_expansion():
    policy = WorkflowPolicy.default()
    nav = policy.getNavigation()
    assert nav.getMode() == NavigationMode.STEP
    assert nav.expandsSteps(P.ACQUISITION) is False


def test_base_plugin_policy_hook_returns_default_container():
    from sciens.spectracs.plugin_sdk.base.SpectralPlugin import SpectralPlugin
    policy = SpectralPlugin().policy()
    assert isinstance(policy, WorkflowPolicy)
    assert policy.getNavigation().getMode() == NavigationMode.STEP


def test_plugin_sdk_facade_exports_policy_and_metadata_form_view():
    import sciens.spectracs.plugin_sdk as sdk
    for name in ("NavigationMode", "NavigationPolicy", "WorkflowPolicy", "MetadataFormView"):
        assert hasattr(sdk, name), name
        assert name in sdk.__all__, name


# --- the PREDICTIVE plan (SPEC_settled_measurement.md §27.16/N1-N2) ------------------------------------
# The live chevron used to be built by a second, inline copy of stops() inside AbstractPluginExecutionView.
# The one thing that copy did differently is these three tests: it walks a PREDICTED phase list, so a new
# run shows the road ahead before the computed phases have any steps. ⛔ Merging the two by dropping the
# prediction would have silently shortened every new run's chevron.

def test_a_planned_phase_with_no_steps_still_earns_a_stop():
    wf = _workflow({P.ACQUISITION: ["Reference", "Sample"]})     # PROCESSING/EVALUATION not populated yet
    planned = [P.ACQUISITION, P.PROCESSING, P.EVALUATION]
    stops = NavigationModel.stops(wf, NavigationPolicy.default(), plannedPhases=planned)
    assert _phaseTypes(stops) == planned
    assert _labels(stops) == ["Acquisition", "Processing", "Evaluation"]


def test_without_a_planned_list_an_empty_phase_is_still_skipped():
    # ⛔ The old behaviour must be untouched: `plannedPhases=None` is exactly today's model.
    wf = _workflow({P.ACQUISITION: ["Reference"]})
    assert _phaseTypes(NavigationModel.stops(wf, NavigationPolicy.default())) == [P.ACQUISITION]


def test_the_plan_expands_steps_where_the_policy_says_so_and_predicts_the_rest():
    wf = _workflow({P.ACQUISITION: ["Reference", "Sample"]})
    policy = NavigationPolicy(NavigationMode.AUTO_ADVANCE, stepChevronPhases={P.ACQUISITION})
    stops = NavigationModel.stops(wf, policy, plannedPhases=[P.ACQUISITION, P.PROCESSING])
    assert _labels(stops) == ["Reference", "Sample", "Processing"]
    assert [s.kind for s in stops] == [NavStopKind.STEP, NavStopKind.STEP, NavStopKind.PHASE]
    assert stops[0].step is not None and stops[2].step is None
