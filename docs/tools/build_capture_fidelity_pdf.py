#!/usr/bin/env python3
"""
Generator for the internal *Capture Fidelity* documentation PDF.

    SOURCE OF TRUTH:  docs/DOC_capture_fidelity.md   <- edit the prose THERE, never the PDF
    OUTPUT:           ../spectracs-docs/internal/Spectracs_CaptureFidelity.pdf

The markdown file is the master document; this script only renders it. It converts a deliberately
SMALL markdown subset (see `_render_block` / `_inline`) to a print-styled HTML page and drives
headless Chrome to produce the PDF — the same mechanism as `build_capability_status_pdf.py`, so the
toolchain requirement stays "Chrome, and nothing else".

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_capture_fidelity_pdf.py            # -> spectracs-docs/internal/
    python3 docs/tools/build_capture_fidelity_pdf.py --out X.pdf

Supported markdown: headings (#..####), paragraphs, `-`/`1.` lists (one nesting level), GFM pipe
tables, fenced code blocks, blockquotes (rendered as call-out boxes), `---` rules, `**bold**`,
`*italic*`, `` `code` ``, links, and `![alt](path)` images (embedded as data URIs; paths are
resolved against the repo root and the sibling spectracs-references tree).
Markers: `<!--TOC-->` inserts the table of contents, `<!--PAGEBREAK-->` forces a page break.
"""
import argparse
import base64
import html as _html
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))                     # .../spectracsPy
SOURCE_MD = os.path.join(REPO, "docs", "DOC_capture_fidelity.md")
DEFAULT_OUT = os.path.abspath(os.path.join(
    REPO, "..", "spectracs-docs", "internal", "Spectracs_CaptureFidelity.pdf"))
IMAGE_ROOTS = [REPO, os.path.join(REPO, "docs"),
               os.path.abspath(os.path.join(REPO, "..", "spectracs-references")),
               os.path.abspath(os.path.join(REPO, "..", "spectracs-references", "tmp"))]


# --------------------------------------------------------------------------- inline markup

def _inline(text):
    """Escape, then apply inline markup. Code spans are protected from the other rules."""
    spans = []

    def stash(match):
        spans.append(_html.escape(match.group(1)))
        return "\x00%d\x00" % (len(spans) - 1)

    text = re.sub(r"`([^`]+)`", stash, text)
    text = _html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: "<code>%s</code>" % spans[int(m.group(1))], text)
    return text


def _image(alt, path):
    for root in IMAGE_ROOTS:
        candidate = path if os.path.isabs(path) else os.path.join(root, path)
        if os.path.exists(candidate):
            mime = mimetypes.guess_type(candidate)[0] or "image/png"
            with open(candidate, "rb") as handle:
                data = base64.b64encode(handle.read()).decode()
            caption = ("<figcaption>%s</figcaption>" % _inline(alt)) if alt else ""
            return ('<figure><img src="data:%s;base64,%s" alt="%s">%s</figure>'
                    % (mime, data, _html.escape(alt), caption))
    return '<p class="missing">[missing image: %s]</p>' % _html.escape(path)


# --------------------------------------------------------------------------- block parsing

def _table(rows):
    """rows: list of raw '| a | b |' lines; row 1 is the header, row 2 the alignment separator."""
    def cells(line):
        return [c.strip() for c in line.strip().strip("|").split("|")]

    head = cells(rows[0])
    aligns = []
    for spec in cells(rows[1]):
        aligns.append("right" if spec.endswith(":") and not spec.startswith(":")
                      else "center" if spec.startswith(":") and spec.endswith(":") else "left")
    out = ["<table><thead><tr>"]
    for index, cell in enumerate(head):
        out.append('<th style="text-align:%s">%s</th>' % (aligns[index] if index < len(aligns) else "left",
                                                          _inline(cell)))
    out.append("</tr></thead><tbody>")
    for line in rows[2:]:
        out.append("<tr>")
        for index, cell in enumerate(cells(line)):
            out.append('<td style="text-align:%s">%s</td>'
                       % (aligns[index] if index < len(aligns) else "left", _inline(cell)))
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _list(items, ordered):
    tag = "ol" if ordered else "ul"
    out = ["<%s>" % tag]
    depth = 0
    for indent, text in items:
        level = 1 if indent >= 2 else 0
        while depth < level:
            out.append("<ul>")
            depth += 1
        while depth > level:
            out.append("</ul>")
            depth -= 1
        out.append("<li>%s</li>" % _inline(text))
    out.extend(["</ul>"] * depth)
    out.append("</%s>" % tag)
    return "".join(out)


def markdown_to_html(text):
    """Return (body_html, toc_entries). toc_entries = [(level, title, anchor)]."""
    text = re.sub(r"<!--(?!TOC|PAGEBREAK)[\s\S]*?-->", "", text)
    lines = text.split("\n")
    out, toc = [], []
    index, slug_counts = 0, {}

    def anchor_for(title):
        base = re.sub(r"[^a-z0-9]+", "-", re.sub(r"[*`]", "", title).lower()).strip("-") or "section"
        slug_counts[base] = slug_counts.get(base, 0) + 1
        return base if slug_counts[base] == 1 else "%s-%d" % (base, slug_counts[base])

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue
        if stripped == "<!--TOC-->":
            out.append("\x01TOC\x01")
            index += 1
            continue
        if stripped == "<!--PAGEBREAK-->":
            out.append('<div class="pagebreak"></div>')
            index += 1
            continue
        if re.fullmatch(r"-{3,}", stripped):
            out.append("<hr>")
            index += 1
            continue

        match = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if match:
            level, title = len(match.group(1)), match.group(2).strip()
            anchor = anchor_for(title)
            if level >= 2:
                toc.append((level, title, anchor))
            out.append('<h%d id="%s">%s</h%d>' % (level, anchor, _inline(title), level))
            index += 1
            continue

        if stripped.startswith("```"):
            index += 1
            block = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            index += 1
            out.append("<pre><code>%s</code></pre>" % _html.escape("\n".join(block)))
            continue

        match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if match:
            out.append(_image(match.group(1), match.group(2)))
            index += 1
            continue

        if stripped.startswith(">"):
            block = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                block.append(lines[index].strip()[1:].strip())
                index += 1
            paragraphs = [p for p in "\n".join(block).split("\n\n") if p.strip()]
            out.append('<blockquote>%s</blockquote>'
                       % "".join("<p>%s</p>" % _inline(p.replace("\n", " ")) for p in paragraphs))
            continue

        if stripped.startswith("|"):
            block = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                block.append(lines[index])
                index += 1
            if len(block) >= 2:
                out.append(_table(block))
            continue

        match = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if match:
            ordered = not match.group(2) in ("-", "*")
            items = []
            while index < len(lines):
                item = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[index])
                if item:
                    items.append((len(item.group(1)), item.group(3).strip()))
                    index += 1
                elif (lines[index].strip() and not lines[index].strip().startswith(("|", ">", "#", "```"))
                      and lines[index].startswith((" ", "\t")) and items):
                    items[-1] = (items[-1][0], items[-1][1] + " " + lines[index].strip())
                    index += 1
                else:
                    break
            out.append(_list(items, ordered))
            continue

        block = []
        while index < len(lines) and lines[index].strip() and not re.match(
                r"^\s*(#{1,4}\s|[-*]\s|\d+\.\s|\||>|```|!\[|<!--)", lines[index]) \
                and not re.fullmatch(r"-{3,}", lines[index].strip()):
            block.append(lines[index].strip())
            index += 1
        if block:
            paragraph = " ".join(block)
            # A paragraph opening with "→ " is a cross-reference into the knowledge base (Appendix A);
            # it gets its own compact style rather than reading as body text.
            css_class = ' class="seealso"' if paragraph.startswith("→ ") else ""
            out.append("<p%s>%s</p>" % (css_class, _inline(paragraph)))
        else:
            index += 1

    body = "\n".join(out)
    toc_html = ['<nav class="toc"><div class="toc-title">Contents</div>']
    for level, title, anchor in toc:
        toc_html.append('<div class="toc-%d"><a href="#%s">%s</a></div>' % (level, anchor, _inline(title)))
    toc_html.append("</nav>")
    return body.replace("\x01TOC\x01", "".join(toc_html)), toc


# --------------------------------------------------------------------------- page shell

CSS = """
:root { --green:#3f7d3f; --green-dk:#2f5d2f; --ink:#1c211c; --muted:#5c655c;
        --line:#d9ded9; --panel:#f5f8f5; --accent:#7a4b28; --code:#f0f2f0; }
@page { size: A4; margin: 17mm 15mm 16mm 15mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin:0; color:var(--ink); background:#fff;
       font:10.6pt/1.5 "Segoe UI","Helvetica Neue",Arial,sans-serif; }
h1 { font-size:23pt; line-height:1.15; margin:0 0 6px; color:var(--ink); letter-spacing:-0.3px; }
h1 + p { font-size:12pt; color:var(--muted); margin:0 0 4px; }
h2 { font-size:14pt; color:var(--green-dk); margin:22px 0 7px; padding-bottom:4px;
     border-bottom:2px solid var(--green); break-after:avoid; }
h3 { font-size:11.6pt; color:var(--ink); margin:16px 0 5px; break-after:avoid; }
h4 { font-size:10.6pt; color:var(--accent); margin:12px 0 4px; break-after:avoid; }
p { margin:6px 0; }
ul,ol { margin:6px 0; padding-left:20px; }
li { margin:3px 0; }
ul ul { margin:2px 0; }
strong { color:#0e120e; }
code { font-family:"DejaVu Sans Mono",Consolas,monospace; font-size:0.87em;
       background:var(--code); padding:1px 4px; border-radius:3px; }
pre { background:var(--code); border:1px solid var(--line); border-radius:6px;
      padding:9px 11px; overflow:hidden; break-inside:avoid; margin:9px 0; }
pre code { background:none; padding:0; font-size:8.6pt; line-height:1.4; white-space:pre-wrap; }
a { color:var(--green-dk); text-decoration:none; }
hr { border:0; border-top:1px solid var(--line); margin:18px 0; }
/* Tall tables must be allowed to flow across pages — forcing the whole table to stay together
   pushes the overflow rows onto a page of their own. Break BETWEEN rows instead, and repeat the
   header on each continuation page. */
table { border-collapse:collapse; width:100%; margin:10px 0; font-size:9.3pt; break-inside:auto; }
thead { display:table-header-group; }
tr { break-inside:avoid; }
th { background:var(--panel); border:1px solid var(--line); padding:5px 7px;
     color:var(--green-dk); font-weight:700; }
td { border:1px solid var(--line); padding:5px 7px; vertical-align:top; }
tbody tr:nth-child(even) td { background:#fafcfa; }
blockquote { margin:11px 0; padding:9px 13px; background:#fbf7ef; border-left:4px solid #c8a24a;
             border-radius:0 6px 6px 0; break-inside:avoid; }
blockquote p { margin:4px 0; }
figure { margin:12px 0; break-inside:avoid; text-align:center; }
figure img { max-width:100%; border:1px solid var(--line); border-radius:6px; }
figcaption { font-size:8.8pt; color:var(--muted); margin-top:5px; text-align:left; }
.missing { color:#b03030; font-style:italic; }
.seealso { font-size:9pt; color:var(--green-dk); background:var(--panel);
           border-left:3px solid var(--green); border-radius:0 4px 4px 0;
           padding:5px 11px; margin:9px 0; break-inside:avoid; }
.seealso a { font-weight:600; }
.pagebreak { break-after:page; }
header.doc { border-bottom:3px solid var(--green); padding-bottom:12px; margin-bottom:16px; }
.brand { font-size:8.6pt; letter-spacing:3.2px; color:var(--green); font-weight:700;
         text-transform:uppercase; }
.meta { margin-top:10px; font-size:9pt; color:var(--muted); }
.meta b { color:var(--ink); }
.toc { background:var(--panel); border:1px solid var(--line); border-radius:7px;
       padding:11px 15px; margin:14px 0 4px; break-inside:avoid; font-size:9.5pt; }
.toc-title { font-weight:700; color:var(--green-dk); margin-bottom:5px;
             text-transform:uppercase; letter-spacing:1.4px; font-size:8.6pt; }
.toc-2 { margin:2px 0; font-weight:600; }
.toc-3 { margin:1px 0 1px 16px; color:var(--muted); }
.foot { margin-top:22px; padding-top:9px; border-top:1px solid var(--line);
        font-size:8.4pt; color:var(--muted); }
"""

SHELL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title><style>{css}</style></head>
<body><header class="doc"><div class="brand">Spectracs &middot; internal documentation</div></header>
{body}
<div class="foot">Spectracs &middot; internal engineering documentation. Generated from
<code>docs/DOC_capture_fidelity.md</code> by <code>docs/tools/build_capture_fidelity_pdf.py</code> &mdash;
edit the markdown and re-run; never hand-edit this PDF.</div>
</body></html>"""


def find_chrome():
    for exe in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        found = shutil.which(exe)
        if found:
            return found
    raise SystemExit("No Chrome/Chromium on PATH — needed to render the PDF.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--source", default=SOURCE_MD)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--html", action="store_true", help="also keep the intermediate HTML next to --out")
    args = parser.parse_args()

    with open(args.source, encoding="utf-8") as handle:
        markdown = handle.read()
    body, toc = markdown_to_html(markdown)
    # Cross-references into the knowledge base are only useful if they resolve. Fail loudly rather
    # than shipping a PDF with dead links (they are silent in a PDF — nothing looks broken).
    anchors = set(re.findall(r'id="([^"]+)"', body))
    dangling = sorted({t for t in re.findall(r'href="#([^"]+)"', body)} - anchors)
    if dangling:
        raise SystemExit("dangling internal link(s) — no heading has these anchors:\n  "
                         + "\n  ".join(dangling))
    title = next((t for lvl, t, _ in toc), "Spectracs — Capture Fidelity")
    page = SHELL.format(title=_html.escape("Spectracs — Capture Fidelity"), css=CSS, body=body)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    if args.html:
        with open(os.path.splitext(args.out)[0] + ".html", "w", encoding="utf-8") as handle:
            handle.write(page)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as handle:
        handle.write(page)
        html_path = handle.name
    try:
        subprocess.run([find_chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        "--run-all-compositor-stages-before-draw", "--virtual-time-budget=4000",
                        "--print-to-pdf=%s" % args.out, "file://%s" % html_path],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        os.unlink(html_path)
    print("wrote %s  (%d sections)" % (args.out, len(toc)))


if __name__ == "__main__":
    main()
