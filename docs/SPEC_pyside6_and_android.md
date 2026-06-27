# Spec — QtCharts → pyqtgraph (license-clean charting) + Android groundwork

Status: **IMPLEMENTED 2026-06-27 (charting). Android groundwork = future effort (§5).**
Scope: PySide6 desktop app. Goal: remove the only GPL-tainted Qt component (Qt Charts) so the app
can ship closed-source under PySide6's LGPLv3, and lay the groundwork for a later Android build.

> **Implementation notes (2026-06-27).** All three charts ported to pyqtgraph; `grep -rn QtCharts`
> is clean. Two findings refined the plan during implementation: (a) the calibration "spline" was
> never a spline — it's the calibration **cubic polynomial** sampled, so D6's scipy spline + <4-point
> guard was unnecessary; (b) the import-preview chart was **dead code** (never added to its layout),
> so it was removed rather than ported. D5 minor deviation: the caller's two `.chart.setTitle(...)`
> calls became `.setTitle(...)`. Verified headless: ring buffer caps at 200, axes freeze to the first
> spectrum, mean is one persistent curve, `clearGraph` resets state. **In-app check (2026-06-27):** one
> of the two graph views was visually confirmed working in the running app; the other could not be
> reached yet due to a *separate, unrelated* issue in that flow (not caused by this migration) — so the
> charting migration is considered working pending the second view's visual check once that flow is
> fixed. Dep: numpy pinned `<2` (1.26.4) because pyqtgraph's install pulled numpy 2.x, breaking the
> numpy-1.x deps.

---

## 1. Problem (current state, as found)

- The app is **already 100% PySide6** (6.5.0) — zero PyQt anywhere. The original "migrate to PySide6
  for license reasons" goal is **already met for the core** (QtWidgets / QtGui / QtCore / QtSvg are
  all LGPLv3 → fine for closed-source with dynamic linking).
- **The actual license leak is Qt Charts.** Qt Charts is **NOT available under LGPL** — it is
  **GPLv3 or commercial only**. While `PySide6.QtCharts` is in use, shipping closed-source triggers
  GPLv3 obligations (or requires a paid commercial Qt license). Swapping bindings buys nothing while
  QtCharts remains.
- QtCharts is used in exactly **3 files** (small, well-bounded surface):

  | File | What it draws | QtCharts API |
  |---|---|---|
  | `view/spectral/spectralJob/widget/SpectralJobGraphViewModule.py` | **Main spectrum graph** — live, multi-curve, custom axes | `QChartView` (subclassed), `QChart`, `QLineSeries`×N, `QValueAxis` |
  | `view/spectral/spectralJob/importSpectrum/SpectralJobImportViewModule.py` | Import preview — one static line | `QChart`, `QLineSeries`, `QChartView` |
  | `view/settings/spectral/spectrometer/acquisition/device/calibration/SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule.py` | Calibration plot — points + smooth fit | `QScatterSeries`, `QSplineSeries`, `QChart`, `QChartView` |

- The main graph is **live, per-frame**: `SpectralJobWidgetViewModule.py:83-84` calls `updateGraph()`
  on two graph instances on every `SpectrumVideoThread.videoThreadSignal` (queued to the GUI thread).
  - `PLOT_SPECTRA` policy: creates a **new `QLineSeries` every frame and never removes it** (random
    gray pen each) → an intentional overlay/waterfall of all captured spectra. Grows **unbounded**.
  - `PLOT_SPECTRA_MEAN` policy: `removeAllSeries()` then rebuilds one mean curve per frame
    (accumulating samples via `np.vstack`).

---

## 2. Decisions locked in (from discussion)

| # | Decision | Choice |
|---|----------|--------|
| D1 | Charting library | **pyqtgraph** (MIT) for **all three** plots — single stack, no matplotlib |
| D2 | Why pyqtgraph over matplotlib | Closes license gap **and** Android-compat gap in one move; faster on live data; scipy (already a dep) covers the spline. matplotlib is slow for live + painful on Android |
| D3 | `PLOT_SPECTRA` overlay | **Option B — bounded ring buffer.** Preserve the waterfall look (intent confirmed: show all series, aggregate curve drawn separately) but cap to the last **N = 200** curves (tunable). Fixes the latent unbounded-growth bug |
| D4 | Main-graph axes | **Frozen to the first spectrum (strict parity)** — pyqtgraph autorange must be explicitly disabled. (Autorange considered and rejected for now to keep behavior identical) |
| D5 | Public API of ported widgets | **Unchanged.** `updateGraph / clearGraph / updateAxes / get/setModuleParameters` stay byte-for-byte so callers (`SpectralJobWidgetViewModule`) are untouched. Only internals/base class change |
| D6 | Calibration spline | Replace `QSplineSeries` with a **scipy-sampled spline drawn as a line**; **guard <4 points** (fall back to a straight line / lower degree) since `make_interp_spline(k=3)` needs ≥4 strictly-increasing x |
| D7 | Dependency management | **Keep PyCharm-managed project venv** for now. A proper `requirements.txt` is **deferred to the Android phase** (explicit prerequisite there, not now) |
| D8 | Theme | **One pyqtgraph theme adapter** over `ApplicationStyleLogicModule` (transparent bg, axis text/grid colors, pens) — built once, reused by all three plots |

---

## 3. Constraints / invariants (the rubber-duck list)

These must hold throughout the migration:

1. **Behavior parity first.** The port must not silently "improve" semantics. The overlay (D3), the
   frozen axes (D4), and the two policies are preserved exactly (modulo the bounded N).
2. **Ring-buffer ownership (D3).** Hold a `deque(maxlen=N)` of `PlotDataItem` handles; on overflow,
   **explicitly `removeItem()`** the evicted curve (pyqtgraph does not free it automatically).
3. **`clearGraph` resets all state.** Must clear plot items, reset the deque, and reset
   `allSpectraValues` (the mean accumulator) — otherwise state leaks across jobs.
4. **GUI-thread only.** pyqtgraph updates must never be called directly from the worker thread;
   they continue to arrive via the existing queued signal.
5. **Public API stability (D5).** Callers do not change. Verified by grep after each port.
6. **Two stacks coexist during phases 1–3.** QtCharts and pyqtgraph both imported until Phase 4's
   removal sweep — do **not** rip QtCharts out early.
7. **License obligation is triggered by *use*, not presence.** QtCharts ships inside
   `PySide6-Addons`; we cannot drop that wheel, but "done" = **zero `QtCharts` imports** (grep-proven).

---

## 4. Implementation phases & steps

> No implementation until explicitly requested. This is the agreed sequence.

| Phase | Step | Action | Risk / note | Done when |
|---|---|---|---|---|
| **0 · Prep & theme** | 0.1 | Add `pyqtgraph` to project venv (PyCharm) | requirements.txt deferred (D7) | imports in venv |
| | 0.2 | Build theme adapter: `ApplicationStyleLogicModule` → pyqtgraph (`setBackground` transparent, `AxisItem` text/grid colors, `mkPen` primary/gray) | do once, reused (D8) | renders a throwaway plot in app theme |
| | 0.3 | Confirm parity checklist in this spec (overlay=last-200, frozen axes, spline guard) | decisions captured before code | checklist green |
| **1 · Import preview** | 1.1 | Port `SpectralJobImportViewModule` single line → `PlotWidget` + adapter | lowest risk; validates embedding & theme | preview visually equivalent |
| **2 · Calibration** | 2.1 | Scatter → `ScatterPlotItem` (circle marker, size parity) | marker look match | points match old plot |
| | 2.2 | `QSplineSeries` → scipy spline sampled to a line, **<4-point guard** (D6) | 2-point case must not throw | smooth curve matches; guard works |
| | 2.3 | `createDefaultAxes` → pyqtgraph autorange | axis-fit parity | axes auto-fit correctly |
| **3 · Main spectrum graph** | 3.1 | Reparent class `QChartView` → `pg.PlotWidget`; drop `QChart`/`setChart`; keep public API (D5) | base-class rewrite | constructs & embeds; caller unchanged |
| | 3.2 | `PLOT_SPECTRA`: `deque(maxlen=200)` of curves, random-gray pen each, evict oldest (D3, C2) | ring-buffer correctness | overlay waterfall identical, bounded to N |
| | 3.3 | `PLOT_SPECTRA_MEAN`: one persistent curve via `setData`; keep `np.vstack` mean | don't accumulate curves here | mean curve correct, single line |
| | 3.4 | Port `updateAxes` — **frozen to first spectrum** (D4) | must disable pyqtgraph autorange | range frozen to frame 1 (parity) |
| | 3.5 | `clearGraph` resets deque + `allSpectraValues` + items (C3) | state leak across jobs | new job starts clean |
| **4 · Excise QtCharts** | 4.1 | `grep -rn QtCharts` → remove every remaining import/comment | stray refs | grep returns nothing |
| | 4.2 | Record license resolution in `docs/KNOWLEDGE_BASE.md` | — | noted |
| **5 · Verify & regress** | 5.1 | Run app via run-recipe through **virtual-device** path; confirm plots live | needs virtual camera | app boots clean; **1 of 2 graph views visually confirmed** (2026-06-27); 2nd blocked by an unrelated flow issue, pending |
| | 5.2 | Build both `.spec` files; add pyqtgraph `hiddenimports` if needed | PyInstaller lazy imports | Linux + Windows specs build & run |
| | 5.3 | Brief Android-readiness note | sets up next effort | note appended below |

---

## 5. Android groundwork (future effort — not in scope here)

Captured so the charting work doesn't paint us into a corner; **separate spec/effort later.**

- **Why pyqtgraph helps:** pure Python over Qt + numpy (already required), no extra native deps —
  best mobile story of the "real" plotting libs. QtCharts removal also removes a GPL component from
  any Android build.
- **The real Android blockers are elsewhere** (not charting):
  - `cv2` (OpenCV), `scipy`, `skimage`, `pandas` — no free PySide-Android wheels; each needs a
    recipe / cross-compile.
  - `usb` (pyusb) + serial spectrometer — Android has no POSIX serial; needs USB-OTG + Android
    permission APIs → a **rewrite** of the device layer, not a port.
- **Open product question for that phase:** full app on Android vs. a thin mobile companion
  (view/connect only, no on-device OpenCV/serial calibration).
- **Prerequisite carried over:** a real `requirements.txt` (D7) before any Android packaging.

---

## 6. Out of scope

- Any change to the binding (already PySide6).
- matplotlib (rejected, D2).
- The visual-harmonization work (separate spec).
- Actual Android packaging (section 5 is groundwork only).
