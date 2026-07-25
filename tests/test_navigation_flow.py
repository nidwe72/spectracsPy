# M2 (B1) unit tests for the pure navigation-decision logic (NavigationFlow). No Qt: exercises terminal
# detection and the AUTO_ADVANCE jump target over a synthetic stops list.

from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType as P
from sciens.spectracs.plugin_sdk.policy.NavigationMode import NavigationMode
from sciens.spectracs.logic.spectral.navigation.NavStop import NavStop, NavStopKind
from sciens.spectracs.logic.spectral.navigation.NavigationFlow import NavigationFlow as F


def _phaseStop(phaseType):
    return NavStop(NavStopKind.PHASE, phaseType, str(phaseType))


def _stepStop(phaseType, label):
    return NavStop(NavStopKind.STEP, phaseType, label, step=object())


# A should-be DEV chevron: [Reference][Sample][Processing][Evaluation][Metadata][Publishing]
_DEV_STOPS = [
    _stepStop(P.ACQUISITION, "Reference"),
    _stepStop(P.ACQUISITION, "Sample"),
    _phaseStop(P.PROCESSING),
    _phaseStop(P.EVALUATION),
    _phaseStop(P.METADATA),
    _phaseStop(P.PUBLISHING),
]


def test_terminal_detection():
    assert F.isTerminal(_DEV_STOPS, 5) is True
    assert F.isTerminal(_DEV_STOPS, 4) is False
    assert F.isTerminal([], 0) is True


def test_last_acquisition_index_and_boundary():
    assert F.lastAcquisitionIndex(_DEV_STOPS) == 1  # the "Sample" step stop
    assert F.isAtAcquisitionBoundary(_DEV_STOPS, 1) is True
    assert F.isAtAcquisitionBoundary(_DEV_STOPS, 0) is False  # Reference is not the LAST acquisition stop
    assert F.lastAcquisitionIndex([_phaseStop(P.PROCESSING)]) is None


def test_halt_index_prefers_metadata_else_final():
    assert F.haltIndex(_DEV_STOPS) == 4  # the Metadata stop
    noMeta = [s for s in _DEV_STOPS if s.phaseType != P.METADATA]
    assert F.haltIndex(noMeta) == len(noMeta) - 1  # no metadata -> final (Publishing)


def test_auto_advance_jumps_from_acquisition_boundary_to_metadata():
    # Next off "Sample" (index 1) -> jump to Metadata (index 4).
    assert F.forwardTarget(_DEV_STOPS, 1, NavigationMode.AUTO_ADVANCE) == 4


def test_auto_advance_reference_is_a_plain_step_not_a_jump():
    # Next off "Reference" (index 0) -> plain step to "Sample" (index 1); the jump only fires at the boundary.
    assert F.forwardTarget(_DEV_STOPS, 0, NavigationMode.AUTO_ADVANCE) == 1


def test_auto_advance_after_landing_walks_normally():
    # From Metadata (4) a further Next steps to Publishing (5); from Publishing it FINISHES.
    assert F.forwardTarget(_DEV_STOPS, 4, NavigationMode.AUTO_ADVANCE) == 5
    assert F.forwardTarget(_DEV_STOPS, 5, NavigationMode.AUTO_ADVANCE) is None


def test_step_mode_never_jumps():
    # STEP mode: every forward Next is a single step, even at the acquisition boundary.
    assert F.forwardTarget(_DEV_STOPS, 0, NavigationMode.STEP) == 1
    assert F.forwardTarget(_DEV_STOPS, 1, NavigationMode.STEP) == 2
    assert F.forwardTarget(_DEV_STOPS, 5, NavigationMode.STEP) is None


def test_auto_advance_without_metadata_jumps_to_final():
    # A plugin with no metadata: jump from the acquisition boundary lands on the final stop (Publishing).
    stops = [s for s in _DEV_STOPS if s.phaseType != P.METADATA]
    boundary = F.lastAcquisitionIndex(stops)
    assert F.forwardTarget(stops, boundary, NavigationMode.AUTO_ADVANCE) == len(stops) - 1


def test_single_acquisition_phase_stop_is_the_boundary():
    # Default policy (no step-expansion): ACQUISITION is one PHASE stop and is itself the boundary.
    stops = [_phaseStop(P.ACQUISITION), _phaseStop(P.PROCESSING), _phaseStop(P.METADATA)]
    assert F.isAtAcquisitionBoundary(stops, 0) is True
    assert F.forwardTarget(stops, 0, NavigationMode.AUTO_ADVANCE) == 2  # jump to Metadata


# --- Option C (§4.4a, J): canJump gates the AUTO_ADVANCE jump so a revisit without a re-capture steps normally ---

def test_can_jump_true_still_jumps_from_the_boundary():
    # A FRESH capture pass (canJump=True, the default) jumps from the boundary to Metadata — unchanged behaviour.
    assert F.forwardTarget(_DEV_STOPS, 1, NavigationMode.AUTO_ADVANCE, canJump=True) == 4


def test_can_jump_false_steps_one_at_a_time_on_revisit():
    # A revisit whose PROCESSING was already computed (canJump=False): Next off the boundary steps to the next
    # stop (Processing, index 2) instead of skipping to Metadata — the user browses the computed phases.
    assert F.forwardTarget(_DEV_STOPS, 1, NavigationMode.AUTO_ADVANCE, canJump=False) == 2


def test_can_jump_false_does_not_affect_non_boundary_or_step_mode():
    # Away from the boundary, or in STEP mode, canJump is irrelevant — every Next is already a plain step.
    assert F.forwardTarget(_DEV_STOPS, 0, NavigationMode.AUTO_ADVANCE, canJump=False) == 1
    assert F.forwardTarget(_DEV_STOPS, 1, NavigationMode.STEP, canJump=False) == 2
