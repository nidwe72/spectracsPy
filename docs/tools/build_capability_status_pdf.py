#!/usr/bin/env python3
"""
Generator for the colleague-facing Capability-Proof *current-state* status report (PDF).

Documented in SPEC_capability_proof.md §11.8. This is the single source of truth for that PDF —
edit the copy/figures here and re-run to regenerate; do not hand-edit the PDF.

HOW TO UPDATE
-------------
1. (If the UI changed) re-take the two Roast-Ampel screenshots from the running app:
     - LIMS_IMG  = the Publishing -> "Send to LIMS" step (the plain verdict the miller always sees)
     - EVAL_IMG  = the Evaluation -> "Evaluation (new)" tab (the analytical gauge, optional detail)
   and point the two constants below at them.
2. Edit the report copy / stats in the HTML string below as the evidence evolves.
3. Run:  python3 docs/tools/build_capability_status_pdf.py
   (needs Pillow + a headless Chrome/Chromium on PATH.)
The PDF is written to OUT_PDF (spectracs-references/tmp/, alongside the other deliverables).
"""
import base64, io, os, subprocess, tempfile, textwrap, shutil
from PIL import Image

# --- inputs: the two live Ampel screenshots (update these when the UI changes) -----------------
LIMS_IMG = os.path.expanduser("~/ksnip_20260724-071903.png")   # Send-to-LIMS — the everyday verdict
EVAL_IMG = os.path.expanduser("~/ksnip_20260724-072139.png")   # Evaluation (new) — analytical gauge
# --- outputs -----------------------------------------------------------------------------------
OUT_PDF = os.path.expanduser(
    "~/development/spectracs/spectracs-references/tmp/Spectracs_CapabilityProof_status.pdf")


def crop_data_uri(path, max_w=1500, top_frac=0.0, bottom_frac=1.0):
    """Resize (and optionally vertically crop) a screenshot, return a base64 JPEG data URI."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    im = im.crop((0, int(h * top_frac), w, int(h * bottom_frac)))
    w, h = im.size
    if w > max_w:
        im = im.resize((max_w, int(h * max_w / w)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def find_chrome():
    for exe in ("google-chrome", "chromium", "chromium-browser", "google-chrome-stable"):
        p = shutil.which(exe)
        if p:
            return p
    raise SystemExit("No Chrome/Chromium on PATH — needed to render the PDF.")


# LIMS shot: header + verdict pill + publish button (top ~48%). Eval shot: header + gauge + rows (top ~52%).
lims_uri = crop_data_uri(LIMS_IMG, top_frac=0.10, bottom_frac=0.48)
eval_uri = crop_data_uri(EVAL_IMG, top_frac=0.10, bottom_frac=0.52)

HTML = textwrap.dedent(f"""\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Spectracs — Capability Proof: Current State</title>
<style>
  :root {{
    --green:#3f7d3f; --green-dk:#2f5d2f; --ink:#1c211c; --muted:#5c655c;
    --line:#d9ded9; --panel:#f4f7f4; --brown:#7a4b28;
  }}
  * {{ box-sizing:border-box; }}
  html {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  body {{
    margin:0; color:var(--ink); background:#fff;
    font:15px/1.55 "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  }}
  .page {{ max-width:820px; margin:0 auto; padding:34px 40px 46px; }}
  header {{ border-bottom:3px solid var(--green); padding-bottom:14px; margin-bottom:22px; }}
  .brand {{ font-size:13px; letter-spacing:3px; color:var(--green); font-weight:700; text-transform:uppercase; }}
  h1 {{ font-size:26px; margin:6px 0 4px; line-height:1.2; }}
  .sub {{ color:var(--muted); font-size:15px; }}
  .date {{ color:var(--muted); font-size:12.5px; margin-top:6px; }}
  h2 {{ font-size:16px; color:var(--green-dk); margin:26px 0 8px; padding-bottom:4px; border-bottom:1px solid var(--line); }}
  h3 {{ font-size:14.5px; color:var(--ink); margin:20px 0 8px; }}
  p {{ margin:8px 0; }}
  ul {{ margin:8px 0; padding-left:20px; }}
  li {{ margin:5px 0; }}
  strong {{ color:var(--ink); }}
  .lead {{ font-size:15.5px; }}
  .stats {{ display:flex; gap:12px; margin:14px 0 6px; flex-wrap:wrap; }}
  .stat {{ flex:1 1 150px; background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px 14px; }}
  .stat .num {{ font-size:22px; font-weight:700; color:var(--green-dk); }}
  .stat .lab {{ font-size:12px; color:var(--muted); margin-top:2px; }}
  figure {{ margin:14px 0; }}
  figure img {{ width:100%; border:1px solid var(--line); border-radius:8px; display:block; }}
  .verdict {{ background:#eef4ee; border-left:4px solid var(--green); border-radius:6px; padding:12px 16px; margin-top:12px; }}
  .foot {{ margin-top:26px; padding-top:10px; border-top:1px solid var(--line); font-size:11.5px; color:var(--muted); }}
  @page {{ size:A4; margin:14mm; }}
</style>
</head>
<body>
<div class="page">

<header>
  <div class="brand">Spectracs</div>
  <h1>Capability Proof — Current State</h1>
  <div class="sub">Can a low-cost visible-light spectrometer tell good pumpkin oil from over-roasted?</div>
  <div class="date">Internal status report · 24 July 2026</div>
</header>

<p class="lead">The goal is deliberately narrow and practical: reliably distinguish a <strong>good green</strong>
pumpkin oil from an <strong>over-roasted brown</strong> one — and do it without being thrown off by how much oil
happens to be in the sample. That over-roast call is what a mill owner actually needs (over-roasted oil tastes
worse and sells for less). Finer "which green is better" judgements are a matter of taste and out of scope.</p>

<h2>What the data shows</h2>
<div class="stats">
  <div class="stat"><div class="num">~10×</div><div class="lab">separation vs. measurement noise (no cluster overlap)</div></div>
  <div class="stat"><div class="num">≤ 5%</div><div class="lab">change when the same oil is diluted 2 → 3 drops</div></div>
  <div class="stat"><div class="num">4</div><div class="lab">oils measured so far (2 green · 2 brown)</div></div>
</div>
<ul>
  <li><strong>Clear separation.</strong> The pigment ratio (Soret/Q band) separates good-green from
     over-roasted-brown by roughly ten times the measurement noise, with <strong>no overlap</strong> — the worst
     green run still sits above the best brown one.</li>
  <li><strong>Dilution-proof.</strong> The same oil at two and three drops gives essentially the same result
     (within a few percent), far tighter than the gap between different oils. This was the make-or-break
     property, and it holds.</li>
  <li><strong>Understood, not lucky.</strong> We know why it works, and why a sample drifts if left standing too
     long (fine particles slowly settling — physics, not a fault). That drift only ever pushes a green oil
     <em>greener</em>, so it never flips the verdict; a simple fresh-sample routine keeps it in check.</li>
</ul>

<h2>How the result reaches the user</h2>
<p>The science is already wrapped in a form a mill floor can use — a colour "traffic-light" gauge (the
<em>Roast Ampel</em>), shown two ways for two moments:</p>

<h3>What the miller always sees</h3>
<figure><img src="{lims_uri}" alt="Send-to-lab gauge"></figure>
<p>The everyday view. At the point of sending a result onward, the miller sees a single plain verdict —
<strong>GOOD — GREEN</strong> (or "probably too brown") — with a coarse colour zone and <strong>deliberately no
number</strong>. A quick, unambiguous good/over-roasted call, with no figure to second-guess.</p>

<h3>What the miller can see if interested in the detail</h3>
<figure><img src="{eval_uri}" alt="Evaluation gauge"></figure>
<p>Optional, for when the detail behind the verdict matters. The analytical view places the exact number (here
<strong>3.70</strong>) on a green→brown scale with the good/over-roasted threshold marked, above the supporting
colour and band readings.</p>

<p>And preparing a sample is easy: <strong>a few drops of oil in isopropanol and a swirl</strong> — no lab
skills, no special glassware.</p>

<h2>Honest limits</h2>
<p>The result rests on <strong>four oils</strong> (two green, two brown). It is corroborated three independent
ways — <em>price</em>, <em>the eye</em>, and <em>the spectrum</em> all agree — so it reads as real rather than
coincidence, but four is still four. The next step is simply to widen the panel with a few more fresh oils
already on hand, turning strong evidence into settled evidence.</p>

<h2>Bottom line</h2>
<div class="verdict">
  <p style="margin:0"><strong>The capability is demonstrated, not merely hoped for</strong> — and it already
  comes wrapped in a usable form. What remains is confirmation, not a coin-flip. Barring a surprise from the
  wider panel — unlikely, given three signals already agree — this closes as a <strong>GO</strong>.</p>
</div>

<div class="foot">Spectracs · pumpkin-oil VIS spectroscopy · capability-proof gate (milestone V). Figures are
live screenshots of the current build; separation figures from 32 measurement runs across 4 oils.</div>

</div>
</body>
</html>
""")


def main():
    os.makedirs(os.path.dirname(OUT_PDF), exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(HTML)
        html_path = f.name
    try:
        subprocess.run(
            [find_chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={OUT_PDF}", f"file://{html_path}"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        os.unlink(html_path)
    print("wrote", OUT_PDF)


if __name__ == "__main__":
    main()
