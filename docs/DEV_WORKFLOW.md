# Spectracs — Development Workflow

## Mock before you build (Wireloom)

**Best practice.** For any non-trivial **layout / UI-shape** change, sketch it as a **Wireloom** mockup and
agree it *before* writing Qt code. Discussing GUI layout in prose or ASCII is slow and ambiguous; a rendered
wireframe is unambiguous and cheap to iterate.

**Why Wireloom** (chosen 2026-07-10 over PlantUML-salt / ASCII): it is **markup → SVG**, **toolkit-neutral**
(knows nothing about Qt), has real UI primitives (`window/panel/tabs/slider/checkbox/…` + `annotation`
callouts), is authored in one shot by an agent, and **versions in git next to the SPEC** — regenerable forever.
Low-fidelity by design, so feedback stays on *structure*, not pixels.

**How (this repo).**
1. Grammar reference: [`.claude/skills/wireloom-AGENTS.md`](../.claude/skills/wireloom-AGENTS.md). The
   [`wireloom` skill](../.claude/skills/wireloom.md) auto-activates on "mock up / sketch / wireframe a UI".
2. Write the source as a `.wireloom` file in `docs/` beside the SPEC (e.g.
   [`mock_bench_acquisition.wireloom`](mock_bench_acquisition.wireloom)).
3. Render + view: `cd tools/wireloom && npm install wireloom` (one-time), then
   `node render.mjs ../../docs/<name>.wireloom <out>.svg` and `rsvg-convert -o <out>.png <out>.svg`.
4. Iterate the mock with the reviewer, land the agreed version in `docs/`, *then* implement + click-through.

> Mock (agree the shape) → build → **click-through** (verify the pixels). The two practices bracket the work.

## Click-through review (drive-and-observe)

**Definition.** A *click-through review* is verifying a change by **driving the running app along the
real user path** — launching it, navigating and clicking exactly as a user would, and **capturing a
screenshot at each step** — then judging the change from what actually rendered, not from reading the
code or running unit tests.

Use the term in instructions, e.g. *"do a click-through review of the user-admin screen"* or
*"click through the login flow and tell me what looks off."*

### Why
Pieces that pass in isolation still break at the seams. Several Roadmap-#4 bugs were **invisible to
code reading and unit tests** but obvious the moment the app was driven:
- the user table showed "Not authorized" + empty because the page only refreshed at startup;
- the Enabled checkbox rendered as a big green box (inherited button styling);
- a stray stylesheet edit silently broke the *entire* app theme;
- the login button showed a native blue default-frame.

None of these would surface from `import-and-call` tests. They surface from **pixels**.

### How (this repo, headless agent)
The app is PySide6/Qt. An agent drives it offscreen and reads back screenshots:

1. `export PYTHONPATH=".:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server"` and
   `QT_QPA_PLATFORM=offscreen` (see `spectracs-run-recipe`).
2. Boot the **real** `MainContainerViewModule`, set
   `ApplicationContextLogicModule().getNavigationHandler().mainContainerViewModule = mc`, `mc.show()`.
3. Drive the **real** path: log in via `SpectracsPyServerClient().login(...)`, emit
   `userSessionSignal`, navigate by emitting `NavigationSignal` / calling the view's own button
   handlers — don't shortcut past the buttons.
4. `widget.grab().save(path)` at each step; read the PNGs back and look.
5. **Probe, don't just confirm:** logged-out vs logged-in, empty/invalid input, navigate-away-and-back,
   the destructive path behind its guard. A review that's all green checks and no probes is half a review.

> The dedicated `/verify` skill encodes this end-to-end (find the change → reach its surface → drive →
> push on it → report). Prefer it for anything non-trivial. This doc is the project-specific shorthand.

### Caveats
- The `offscreen` platform renders real pixels but won't show truly interactive states (live hover,
  real modal exec); `isVisible()` is `False` until a top-level is shown — probe widget flags with
  `isHidden()` instead.
- Driving the app can hit the **real** server/DB (a local Pyro server may be running). If a step
  creates/deletes data, clean up after (delete the test user you added), and say so.
- A click-through review is runtime observation — **not** a substitute for the change being correct;
  it's how you find out whether it is.
