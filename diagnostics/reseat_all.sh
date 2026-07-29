#!/usr/bin/env bash
# Full mechanical-repeatability sweep (SPEC_capture_quality.md §16.7.1/§16.9.3). Runs cuvette_reseat_probe.py
# once per disturbance arm, tees each to a timestamped folder, and prints the comparison table at the end.
#
#   diagnostics/reseat_all.sh                      # all six arms, 6 changes each (~1h with the relax windows)
#   diagnostics/reseat_all.sh jar none             # just these two (the pair worth running first)
#   CHANGES=4 RELAX=45 diagnostics/reseat_all.sh   # shorter rounds
#
# The arms split by whether the jar is in the beam. The script stops between the two groups and asks you to
# take it out, so run them in the given order rather than one at a time.
#
#   jar IN   none  jar  camera
#   jar OUT  cone  holder  stack
#
# `jar` is the REALISTIC composite: taking the cuvette out and back in necessarily lifts and re-seats the cone
# too, so that arm contains both. `cone` (empty beam, cone only) is what lets you subtract it back out —
# jar-alone = sqrt(jar^2 - cone^2), which is how §16.9.3h derived 2.81 % from a measured 2.84 %.
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server"

DEVICE="${DEVICE:-0}"
CHANGES="${CHANGES:-6}"
RELAX="${RELAX:-60}"
# The probe warms the sensor for 300 s by default (§16.2: settles ~9 min). That is right for the FIRST arm of a
# session and pure waiting for the rest — the sensor does not cool between back-to-back arms. 6 arms at the
# default would be 30 min of warmup alone.
WARMUP="${WARMUP:-300}"
WARMUP_NEXT="${WARMUP_NEXT:-60}"
ROI="${ROI:-665,794,2226,1658}"
COEFFS="${COEFFS:--6.72651743127379e-09,2.68123787138496e-05,0.115548014949371,318.141502522378}"

JAR_IN="none jar camera"
JAR_OUT="cone holder stack"
ARMS="${*:-$JAR_IN $JAR_OUT}"

# Overridable so a staged sweep (different --changes per arm) collects into ONE folder and the closing table
# covers every arm run so far, not just this invocation's.
OUT="${OUT:-../spectracs-references/tmp/reseat_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUT"
echo "→ $OUT"

runArm() {
    warmup="$WARMUP"
    [ -n "$warmedUp" ] && warmup="$WARMUP_NEXT"
    echo
    echo "=============================================================="
    echo "  ARM: $1   ($CHANGES changes, ${RELAX}s relax, ${warmup}s warmup)"
    echo "=============================================================="
    ./venv/bin/python diagnostics/cuvette_reseat_probe.py \
        --device "$DEVICE" --disturb "$1" --changes "$CHANGES" --relax "$RELAX" \
        --warmup "$warmup" --roi "$ROI" --coeffs="$COEFFS" 2>&1 | tee "$OUT/$1.txt"
    warmedUp=1
}

# Group A first (jar in the beam), then prompt once, then group B (empty beam).
for arm in $ARMS; do
    case " $JAR_IN " in *" $arm "*) runArm "$arm";; esac
done
for arm in $ARMS; do
    case " $JAR_OUT " in *" $arm "*)
        if [ -z "$askedToRemove" ]; then
            read -r -p $'\n   >>> TAKE THE JAR OUT — the remaining arms run on an empty beam. Enter when ready '
            askedToRemove=1
        fi
        runArm "$arm";;
    esac
done

echo
echo "=============================================================="
echo "  tilt vs the pre-rebuild rig (§16.9.3, same script)"
echo "=============================================================="
printf '  %-8s %-12s %s\n' arm old today
for arm in $(ls "$OUT" | sed 's/\.txt$//'); do
    case "$arm" in
        jar)    old="2.84 % (composite)";;
        camera) old="0.42 %";;
        holder) old="0.56 %";;
        cone)   old="0.39 %";;
        stack)  old="—";;
        none)   old="0.04-0.09 %";;
        *)      old="—";;
    esac
    # Anchor on the final "TILT vs LEVEL" block: its line STARTS with `tilt`, where the settle-report lines
    # ("untouched control : tilt mean ...") carry it mid-line. Leading `^ *` is what keeps them apart.
    today=$(grep -oE '^ *tilt +mean +[0-9.]+' "$OUT/$arm.txt" 2>/dev/null | tail -1 | grep -oE '[0-9.]+$')
    printf '  %-8s %-12s %s\n' "$arm" "$old" "${today:-see $arm.txt}%"
done
echo
echo "  jar alone (cone removed in quadrature) = sqrt(jar^2 - cone^2)"
echo "  full logs: $OUT"
