# Wireloom render helper

Wireloom is our tool for GUI layout mockups (markup → SVG, toolkit-neutral). See the DSL grammar in
`.claude/skills/wireloom-AGENTS.md`. Reference mock: `docs/mock_bench_acquisition.wireloom`.

```bash
cd tools/wireloom && npm install wireloom      # one-time
node render.mjs ../../docs/mock_bench_acquisition.wireloom /tmp/mock.svg
rsvg-convert -o /tmp/mock.png /tmp/mock.svg     # to view
```
