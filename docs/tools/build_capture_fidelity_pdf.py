#!/usr/bin/env python3
"""
Generator for the internal *Capture Fidelity* documentation PDF.

Also used, via --source/--out/--title, to render the sibling *Light, Pigment and Solvent* document
(see `build_sample_physics_pdf.py`). The renderer is document-agnostic; only the defaults below are
specific to Capture Fidelity.

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


# --------------------------------------------------------------------------- math

# A deliberately tiny formula notation — enough to typeset the metric algebra without pulling in
# KaTeX/MathJax, which would break the "Chrome, and nothing else" toolchain rule. Supported:
#   _{...} ^{...}          subscript / superscript
#   \frac{...}{...}        a real stacked fraction (rule line included)
#   \sqrt{...}             radical
#   a handful of \symbols  (see MATH_SYMBOLS)
# Display form is a ```math fence; inline form is $...$ inside a paragraph.
MATH_SYMBOLS = {
    r"\lambda": "\u03bb", r"\Sigma": "\u03a3", r"\sigma": "\u03c3", r"\Delta": "\u0394",
    r"\mu": "\u03bc", r"\epsilon": "\u03b5", r"\alpha": "\u03b1", r"\beta": "\u03b2",
    # An unlisted \symbol renders as its own literal source text, silently \u2014 so the lowercase Greek
    # letters are listed even where no document uses them yet.
    r"\delta": "\u03b4", r"\gamma": "\u03b3", r"\rho": "\u03c1", r"\tau": "\u03c4",
    r"\theta": "\u03b8", r"\phi": "\u03c6", r"\varphi": "\u03c6", r"\pi": "\u03c0",
    r"\omega": "\u03c9", r"\Omega": "\u03a9", r"\nu": "\u03bd", r"\kappa": "\u03ba",
    r"\eta": "\u03b7", r"\zeta": "\u03b6", r"\xi": "\u03be", r"\psi": "\u03c8",
    r"\Phi": "\u03a6", r"\Theta": "\u0398", r"\Lambda": "\u039b", r"\Pi": "\u03a0",
    r"\cdot": "\u00b7", r"\times": "\u00d7", r"\pm": "\u00b1", r"\approx": "\u2248",
    r"\le": "\u2264", r"\ge": "\u2265", r"\ne": "\u2260", r"\to": "\u2192",
    r"\Rightarrow": "\u21d2", r"\in": "\u2208", r"\infty": "\u221e", r"\propto": "\u221d",
    r"\qquad": "\u2003\u2003", r"\quad": "\u2003", r"\,": "\u2009",
    r"\equiv": "\u2261", r"\ell": "\u2113", r"\ldots": "\u2026", r"\sum": "\u03a3",
    # delimiter sizing hints: ignore the hint, just draw the delimiter
    r"\big(": "(", r"\big)": ")", r"\big[": "[", r"\big]": "]",
    r"\Big(": "(", r"\Big)": ")", r"\Big[": "[", r"\Big]": "]",
    r"\bigg(": "(", r"\bigg)": ")", r"\Bigg(": "(", r"\Bigg)": ")",
    r"\left": "", r"\right": "",
    r"\text{": "\\op{",                                  # \text{...} == \op{...}: upright words
    r"\arg": r"\op{arg}", r"\ln": r"\op{ln}", r"\exp": r"\op{exp}",
    # upright operator names \u2014 an italic "log" reads as l\u00b7o\u00b7g multiplied together
    r"\log": r"\op{log}", r"\mean": r"\op{mean}", r"\median": r"\op{median}",
    r"\max": r"\op{max}", r"\min": r"\op{min}", r"\std": r"\op{sd}",
}


def _math_markup(text, minus=True):
    """Escape, then apply the small formula notation. Returns HTML.

    `minus` converts ASCII hyphens to a real U+2212 minus; it is off for annotation lines, where a
    hyphen is usually punctuation rather than an operator."""
    text = _html.escape(text)
    for token, glyph in sorted(MATH_SYMBOLS.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(token, glyph)
    if minus:
        text = text.replace("-", "\u2212")
    text = re.sub(r"\\op\{([^{}]*)\}", r'<span class="op">\1</span>', text)
    # sub/sup first: after this pass their braces are gone, so \frac can use a brace-free inner match
    for _ in range(3):                                   # allow a little nesting (A_{Q}^{2})
        new = re.sub(r"_\{([^{}]*)\}", r"<sub>\1</sub>", text)
        new = re.sub(r"\^\{([^{}]*)\}", r"<sup>\1</sup>", new)
        if new == text:
            break
        text = new
    # Order matters, and each pass matches brace-free bodies ([^{}]), so an inner construct must be
    # converted BEFORE the outer one that contains it:
    #   \bar  before \frac  — we write \frac{\bar{x}}{...}
    #   \frac before \sqrt  — we write \sqrt{\frac{...}{...}}
    text = re.sub(r"\\bar\{([^{}]*)\}", r'<span class="bar">\1</span>', text)
    for _ in range(3):                                   # innermost \frac first
        new = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}",
                     r'<span class="frac"><span class="num">\1</span>'
                     r'<span class="den">\2</span></span>', text)
        if new == text:
            break
        text = new
    text = re.sub(r"\\sqrt\{([^{}]*)\}", r'<span class="sqrt">\1</span>', text)
    # LAST: literal braces. Substituting these earlier would defeat the _{...} / \frac{}{} patterns,
    # whose bodies are matched with [^{}] and so must not contain braces of their own.
    text = text.replace("\\{", "{").replace("\\}", "}")
    return text


# --------------------------------------------------------------------------- inline markup

def _inline(text):
    """Escape, then apply inline markup. Code spans and $formulas$ are protected from the other rules
    (both are stashed as finished HTML, so the emphasis/link passes cannot reach inside them)."""
    spans = []

    def stash(html_fragment):
        spans.append(html_fragment)
        return "\x00%d\x00" % (len(spans) - 1)

    text = re.sub(r"`([^`]+)`", lambda m: stash("<code>%s</code>" % _html.escape(m.group(1))), text)
    text = re.sub(r"\$([^$\n]+)\$",
                  lambda m: stash('<span class="math-inline">%s</span>' % _math_markup(m.group(1))), text)
    text = _html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    # Non-greedy, and the body MAY contain single asterisks: `**bold with *italic* inside**` is common
    # prose here. The old `[^*]+` body could not match it and the regex then latched onto the NEXT pair
    # of `**`, emphasising the span between two bold runs instead of the runs themselves.
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)
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
            info = stripped[3:].strip().lower()
            index += 1
            block = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            index += 1
            if info == "math":
                # Each non-blank line is one display equation; a line starting with two spaces is a
                # continuation/annotation and is rendered smaller and left-aligned under the formula.
                rendered = []
                for raw in block:
                    if not raw.strip():
                        continue
                    note = raw.startswith("  ")
                    rendered.append('<div class="%s">%s</div>'
                                    % ("math-note" if note else "math-line",
                                       _math_markup(raw.strip(), minus=not note)))
                out.append('<div class="math">%s</div>' % "".join(rendered))
            else:
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
/* Formulas — the ```math fence and $inline$ spans. Serif italic so a variable reads as a variable;
   fractions are real stacked constructions with a rule line. No external math library is involved. */
.math { margin:12px 0; padding:10px 14px; background:var(--panel); border:1px solid var(--line);
        border-left:3px solid var(--green); border-radius:0 6px 6px 0; break-inside:avoid;
        text-align:center; }
.math-line { font-family:"DejaVu Serif",Georgia,"Times New Roman",serif; font-style:italic;
             font-size:11.6pt; line-height:2.0; margin:5px 0; color:#141814; }
.math-note { font-size:8.8pt; font-style:normal; color:var(--muted); text-align:left;
             margin:2px 0 6px 4px; font-family:"Segoe UI",Arial,sans-serif; }
.math-inline { font-family:"DejaVu Serif",Georgia,"Times New Roman",serif; font-style:italic;
               font-size:1.02em; white-space:nowrap; }
.frac { display:inline-block; vertical-align:middle; text-align:center; margin:0 0.25em;
        line-height:1.25; }
.frac .num { display:block; padding:0 0.45em 1px; border-bottom:1.1px solid #141814; }
.frac .den { display:block; padding:1px 0.45em 0; }
.sqrt { border-top:1.1px solid #141814; padding:0 0.2em; margin-left:0.1em; }
.sqrt::before { content:"\\221A"; margin-left:-0.35em; border-top:none; }
.bar { border-top:1.1px solid #141814; padding-top:0.5px; }
.math sub, .math sup, .math-inline sub, .math-inline sup { font-style:normal; font-size:0.68em; }
.math .op, .math-inline .op { font-style:normal; }
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
<code>{source}</code> by <code>{generator}</code> &mdash;
edit the markdown and re-run; never hand-edit this PDF.</div>
</body></html>"""


def _provenance(sourcePath):
    """(source, generator) for the footer, both repo-relative.

    ⚠ The footer used to name this file and `DOC_capture_fidelity.md` literally, so every sibling
    document that borrows this renderer via --source told the reader to edit the wrong markdown.
    The generator is derived by the naming convention the wrappers follow — `DOC_x.md` is built by
    `build_x_pdf.py` — and falls back to this module if no such wrapper exists."""
    source = os.path.relpath(os.path.abspath(sourcePath), REPO)
    stem = os.path.basename(sourcePath)
    if stem.startswith("DOC_") and stem.endswith(".md"):
        wrapper = os.path.join(HERE, "build_%s_pdf.py" % stem[4:-3])
        if os.path.exists(wrapper):
            return source, os.path.relpath(wrapper, REPO)
    return source, os.path.relpath(os.path.abspath(__file__), REPO)


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
    parser.add_argument("--title", default=None,
                        help="document title; defaults to the first heading in the source")
    parser.add_argument("--html", action="store_true", help="also keep the intermediate HTML next to --out")
    args = parser.parse_args()

    with open(args.source, encoding="utf-8") as handle:
        markdown = handle.read()

    # An image directive is matched with re.fullmatch against ONE stripped line, so an alt text that
    # wraps does not raise — it silently falls through to the paragraph branch and the reader gets
    # `...](figures/x.svg)` as body text where a figure should be. Catch it here instead.
    for number, line in enumerate(markdown.split("\n"), start=1):
        stripped = line.strip()
        if stripped.startswith("![") and not re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", stripped):
            raise SystemExit("%s:%d — image directive spans more than one line (the alt text wraps).\n"
                             "  Put the whole ![alt](path) on a single line.\n  %s"
                             % (os.path.basename(args.source), number, stripped[:100]))

    body, toc = markdown_to_html(markdown)
    # Cross-references into the knowledge base are only useful if they resolve. Fail loudly rather
    # than shipping a PDF with dead links (they are silent in a PDF — nothing looks broken).
    anchors = set(re.findall(r'id="([^"]+)"', body))
    dangling = sorted({t for t in re.findall(r'href="#([^"]+)"', body)} - anchors)
    if dangling:
        raise SystemExit("dangling internal link(s) — no heading has these anchors:\n  "
                         + "\n  ".join(dangling))
    title = args.title or "Spectracs — %s" % next((t for lvl, t, _ in toc), "internal documentation")
    source, generator = _provenance(args.source)
    page = SHELL.format(title=_html.escape(title), css=CSS, body=body,
                        source=_html.escape(source), generator=_html.escape(generator))

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
