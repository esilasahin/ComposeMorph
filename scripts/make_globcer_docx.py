#!/usr/bin/env python3
"""Convert the GLOBCER variant of the paper into a Word (.docx) file.

GLOBCER's template is a Word document, so this produces a single-column
Times New Roman 12pt .docx whose text can be pasted into the official
template (or handed in as-is). The conversion goes LaTeX -> HTML ->
.docx via LibreOffice, which must be on PATH.

Figure 2 is redrawn with matplotlib (same numbers as
results/tables/comparison_summary.md, section 2); Figure 1 is a
monospaced block, so it survives as preformatted text.

Usage:
    python3 scripts/make_globcer_version.py     # first, to refresh the .tex
    python3 scripts/make_globcer_docx.py
"""
from __future__ import annotations

import argparse
import base64
import html
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

OPS = ["image", "hostname", "env"]
CHANGED = {"ComposeMorph": [10, 23, 10], "yaml-cpp (dikkatli)": [13, 31, 14],
           "yaml-cpp (naif)": [23, 48, 17]}
PRESERVED = {"ComposeMorph": [100, 100, 100],
             "yaml-cpp (dikkatli)": [87.25, 58.97, 86.21],
             "yaml-cpp (naif)": [0, 0, 0]}

SUPERS = {"-": "\u207b", "1": "\u00b9", "0": "\u2070", "2": "\u00b2"}


def draw_figure(path: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("warning: matplotlib missing, Figure 2 will be a placeholder",
              file=sys.stderr)
        return False
    width = 0.25
    x = range(len(OPS))
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
    for i, label in enumerate(CHANGED):
        off = [xi + (i - 1) * width for xi in x]
        b0 = axes[0].bar(off, CHANGED[label], width=width, label=label)
        b1 = axes[1].bar(off, PRESERVED[label], width=width, label=label)
        # Naif kullanımın %0 çubukları görünmez; değerler yazıyla verilir.
        axes[0].bar_label(b0, fontsize=7, padding=1)
        axes[1].bar_label(b1, fmt="%.0f", fontsize=7, padding=1)
    for ax in axes:
        ax.set_xticks(list(x))
        ax.set_xticklabels(OPS)
    axes[0].set_ylabel("Değişen satır (medyan)")
    axes[1].set_ylabel("Korunan kardeş alanlar (%)")
    axes[1].set_ylim(0, 105)
    axes[0].legend(fontsize="small", loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return True


def strip_math(s: str) -> str:
    s = s.replace(r"\(\geq\)", "≥").replace(r"$\rightarrow$", "→")
    s = s.replace(r"$\times$", "×")

    def math(m):
        body = m.group(1)
        body = body.replace(r"\rightarrow", "→").replace(r"\geq", "≥")
        body = re.sub(r"10\^\{(-?\d+)\}",
                      lambda e: "10" + "".join(SUPERS.get(c, c) for c in e.group(1)),
                      body)
        return body.replace("<", "&lt;").replace(">", "&gt;")

    return re.sub(r"\$([^$]*)\$", math, s)


PROTECT = {r"\%": "\x01", r"\_": "\x02", r"\&": "\x03", r"\$": "\x04",
           r"\{": "\x05", r"\}": "\x06", r"\#": "\x07"}


def inline(s: str, cites: dict[str, int], refs: dict[str, str]) -> str:
    s = re.sub(r"(?<!\\)%.*$", "", s, flags=re.M)          # yorumlar
    for tex, holder in PROTECT.items():                    # kaçışlı karakterler
        s = s.replace(tex, holder)
    s = strip_math(s)
    s = re.sub(r"\\footnote\{(.*?)\}", r" (\1)", s, flags=re.S)
    s = re.sub(r"\\cite\{([^}]*)\}",
               lambda m: "[" + ", ".join(str(cites.get(k.strip(), "?"))
                                          for k in m.group(1).split(",")) + "]", s)
    s = re.sub(r"\\ref\{([^}]*)\}", lambda m: refs.get(m.group(1), "?"), s)
    s = re.sub(r"\\url\{([^}]*)\}", lambda m: "<code>" + html.escape(m.group(1)) + "</code>", s)
    s = re.sub(r"\\texttt\{([^{}]*)\}", lambda m: "<code>" + html.escape(m.group(1)) + "</code>", s)
    s = re.sub(r"\\(?:emph|textit)\{([^{}]*)\}", r"<i>\1</i>", s)
    s = re.sub(r"\\textbf\{([^{}]*)\}", r"<b>\1</b>", s)
    s = re.sub(r"\\textsuperscript\{([^{}]*)\}", r"<sup>\1</sup>", s)
    s = s.replace("``", "“").replace("''", "”")
    # Tire dönüşümü yalnızca düz metinde; kod parçalarında "--" aynen kalmalı
    # (örneğin setCommand({"run", "--workers", "4"})).
    s = "".join(part if part.startswith("<code>")
                else part.replace("---", "—").replace("--", "–")
                for part in re.split(r"(<code>.*?</code>)", s, flags=re.S))
    s = re.sub(r"\\[,;!]", " ", s)
    s = s.replace(r"\ ", " ").replace("~", " ")
    s = re.sub(r"\\[a-zA-Z]+\*?", "", s)                    # kalan komutlar
    s = s.replace("{", "").replace("}", "")
    for tex, holder in PROTECT.items():
        s = s.replace(holder, html.escape(tex[1:]))
    return re.sub(r"[ \t]+", " ", s).strip()


ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


def number_labels(body: str) -> dict[str, str]:
    """Map each \\label key to the number LaTeX would print for it."""
    refs: dict[str, str] = {}
    sec = tab = fig = 0
    for m in re.finditer(r"\\section\{|\\label\{([^}]*)\}", body):
        key = m.group(1)
        if key is None:
            sec += 1
            continue
        if key.startswith("tab:"):
            tab += 1
            refs[key] = ROMAN[tab - 1]
        elif key.startswith("fig:"):
            fig += 1
            refs[key] = str(fig)
        elif sec:
            refs[key] = ROMAN[sec - 1]
    return refs


def split_blocks(body: str) -> list[str]:
    """Split into paragraphs, keeping table/figure environments in one piece.

    Floats contain blank lines, so a plain blank-line split would tear a
    caption away from its float; lists often start on the line right after
    their lead-in sentence, which would otherwise leave the environment
    name in the running text.
    """
    env = re.compile(r"\\begin\{(table|figure|itemize|enumerate)\}"
                     r".*?\\end\{\1\}", re.S)
    blocks: list[str] = []
    pos = 0
    for m in env.finditer(body):
        blocks += re.split(r"\n\s*\n", body[pos:m.start()])
        blocks.append(m.group(0))
        pos = m.end()
    blocks += re.split(r"\n\s*\n", body[pos:])
    return blocks


def convert_table(block: str, cites, refs) -> str:
    caption = re.search(r"\\caption\{(.*?)\}\s*\n", block, re.S)
    label = re.search(r"\\label\{(tab:[^}]*)\}", block)
    rows = re.search(r"\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}", block, re.S)
    out = []
    num = refs.get(label.group(1), "") if label else ""
    if caption:
        out.append(f'<p class="caption"><b>Tablo {num}.</b> '
                   f'{inline(caption.group(1), cites, refs)}</p>')
    if rows:
        body = rows.group(1)
        body = re.sub(r"\\(top|mid|bottom)rule|\\cmidrule\([^)]*\)\{[^}]*\}", "", body)
        html_rows = []
        for line in body.split(r"\\"):
            cells = []
            for cell in line.split("&"):
                # \multicolumn{n}{hiza}{metin} -> n sütuna yayılan tek hücre
                span = re.search(r"\\multicolumn\{(\d+)\}\{[^{}]*\}\{(.*)\}\s*$",
                                 cell.strip(), re.S)
                if span:
                    cells.append((int(span.group(1)),
                                  inline(span.group(2), cites, refs)))
                else:
                    cells.append((1, inline(cell, cites, refs)))
            if any(text for _, text in cells):
                html_rows.append("<tr>" + "".join(
                    (f'<td colspan="{n}">{text}</td>' if n > 1 else f"<td>{text}</td>")
                    for n, text in cells) + "</tr>")
        out.append("<table>" + "".join(html_rows) + "</table>")
    note = re.search(r"\\parbox\{[^}]*\}\{(.*?)\}\s*\n?\\end\{table\}", block, re.S)
    if note:
        out.append(f'<p class="note">{inline(note.group(1), cites, refs)}</p>')
    return "\n".join(out)


def convert_figure(block: str, cites, refs, figure_png: Path | None) -> str:
    caption = re.search(r"\\caption\{(.*)\}\s*\n\s*\\label", block, re.S)
    label = re.search(r"\\label\{(fig:[^}]*)\}", block)
    num = refs.get(label.group(1), "") if label else ""
    out = []
    verb = re.search(r"\\begin\{verbatim\}\n(.*?)\\end\{verbatim\}", block, re.S)
    if verb:
        out.append("<pre>" + html.escape(verb.group(1).rstrip()) + "</pre>")
    elif figure_png is not None:
        # Görüntü HTML'e gömülür; dosya yolu verilirse LibreOffice docx'e
        # bağlantı koyar ve dosya başka bilgisayarda görünmez.
        data = base64.b64encode(figure_png.read_bytes()).decode()
        out.append('<p class="figure"><img width="640" '
                   f'src="data:image/png;base64,{data}"/></p>')
    else:
        out.append('<p class="figure">[Şekil 2 -- görüntü oluşturulamadı]</p>')
    if caption:
        out.append(f'<p class="caption"><b>Şekil {num}.</b> '
                   f'{inline(caption.group(1), cites, refs)}</p>')
    return "\n".join(out)


def build_html(tex: str, figure_png: Path | None) -> str:
    body = tex.split(r"\begin{document}", 1)[1].split(r"\end{document}", 1)[0]
    bib = re.findall(r"\\bibitem\{([^}]*)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})",
                     body, re.S)
    cites = {key: i + 1 for i, (key, _) in enumerate(bib)}
    refs = number_labels(body)
    body = body.split(r"\begin{thebibliography}")[0]
    # Bölüm etiketleri numaralar çözüldükten sonra metinden çıkarılır;
    # tablo/şekil etiketleri float numaralandırmasında hâlâ gerekli.
    body = re.sub(r"\\label\{sec:[^}]*\}", "", body)

    parts: list[str] = []
    section_no = 0
    # Başlık bloğu
    parts.append('<p class="title"><b>C++ Ortamında Konteyner Servis '
                 'Yapılandırmalarının Güvenli Round-Trip Düzenlenmesi</b></p>')
    parts.append('<p class="subtitle"><i>Safe Round-Trip Editing of Container '
                 'Service Configurations in C++</i></p>')
    parts.append('<p class="authors">Esila Şahin<sup>*,1</sup>, Ömer Yıldız<sup>2</sup>, '
                 'Mehmet Berk Kartal<sup>3</sup>, Ahmet Batuhan Canlı<sup>4</sup> '
                 '(<sup>*</sup>: <i>sorumlu yazar</i>)</p>')
    parts.append('<p class="affil"><sup>*</sup>esila.sahin@stu.fsm.edu.tr, '
                 'ORCID: 0009-0007-8858-9540<br/>'
                 '<sup>1</sup><i>Yazılım Mühendisliği Bölümü, Fatih Sultan Mehmet '
                 'Vakıf Üniversitesi, İstanbul, Türkiye</i><br/>'
                 '<sup>2,3,4</sup><i>TÜBİTAK BİLGEM UEKAE, Kocaeli, Türkiye</i></p>')

    body = re.sub(r"\\thispagestyle\{[^}]*\}", "", body)
    body = re.sub(r"\\begin\{center\}.*?\\end\{center\}", "", body, flags=re.S)
    body = re.sub(r"\\noindent\\rule\{[^}]*\}\{[^}]*\}", "", body)

    for block in split_blocks(body):
        block = block.strip()
        if not block:
            continue
        if block.startswith(r"\begin{table}") or r"\begin{table}" in block:
            parts.append(convert_table(block, cites, refs))
        elif r"\begin{figure}" in block:
            png = None if r"\begin{verbatim}" in block else figure_png
            parts.append(convert_figure(block, cites, refs, png))
        elif block.startswith(r"\begin{verbatim}") or block.startswith("{\\footnotesize"):
            code = re.search(r"\\begin\{verbatim\}\n(.*?)\\end\{verbatim\}", block, re.S)
            if code:
                parts.append("<pre>" + html.escape(code.group(1).rstrip()) + "</pre>")
        elif block.startswith(r"\section"):
            title = re.search(r"\\section\{([^}]*)\}", block).group(1)
            section_no += 1
            parts.append(f"<h2>{ROMAN[section_no - 1]}. {html.escape(title)}</h2>")
            rest = block.split("}", 1)[1].strip()
            if rest:
                parts.append(f"<p>{inline(rest, cites, refs)}</p>")
        elif block.startswith(r"\subsection"):
            title = re.search(r"\\subsection\{(.*?)\}\s*$", block, re.M)
            title = title.group(1) if title else ""
            parts.append(f"<h3>{inline(title, cites, refs)}</h3>")
            rest = re.sub(r"\\subsection\{.*?\}\s*", "", block, count=1, flags=re.S).strip()
            if rest:
                parts.append(f"<p>{inline(rest, cites, refs)}</p>")
        elif block.startswith(r"\begin{itemize}") or block.startswith(r"\begin{enumerate}"):
            tag = "ul" if "itemize" in block else "ol"
            items = re.split(r"\\item\s", block)[1:]
            items = [inline(re.sub(r"\\end\{(itemize|enumerate)\}", "", i), cites, refs)
                     for i in items]
            parts.append(f"<{tag}>" + "".join(f"<li>{i}</li>" for i in items) + f"</{tag}>")
        else:
            # \noindent ile başlayan paragraflar (özet, anahtar kelimeler)
            # şablondaki gibi girintisiz kalır.
            cls = ' class="noindent"' if block.startswith("\\noindent") or \
                block.startswith("\\smallskip\\noindent") else ""
            text = inline(block, cites, refs)
            if text:
                parts.append(f"<p{cls}>{text}</p>")

    parts.append("<h2>KAYNAKLAR</h2>")
    for key, entry in bib:
        parts.append(f'<p class="ref">[{cites[key]}] {inline(entry, cites, refs)}</p>')

    style = """
    body { font-family: 'Times New Roman', serif; font-size: 12pt; }
    p { text-align: justify; margin: 0 0 6pt 0; text-indent: 1.2em; }
    p.title { text-align: center; font-size: 14pt; text-indent: 0; }
    p.subtitle, p.authors, p.affil, p.caption, p.figure { text-align: center; text-indent: 0; }
    p.affil, p.caption, p.note, p.ref { font-size: 10pt; }
    p.note, p.noindent { text-indent: 0; }
    p.ref { text-indent: 0; margin-left: 1.5em; }
    h2 { font-size: 12pt; font-weight: bold; margin: 12pt 0 6pt 0; }
    h3 { font-size: 12pt; font-style: italic; font-weight: normal; margin: 10pt 0 4pt 0; }
    pre, code { font-family: 'Courier New', monospace; font-size: 10pt; }
    table { border-collapse: collapse; margin: 0 auto 6pt auto; font-size: 10pt; }
    td { border-top: 0.5pt solid black; border-bottom: 0.5pt solid black;
         padding: 2pt 6pt; }
    """
    return ("<html><head><meta charset='utf-8'><style>" + style +
            "</style></head><body>" + "\n".join(parts) + "</body></html>")


# LibreOffice'in "Body Text" varsayılanı 1,15 satır aralığı ve paragraf
# sonrası 6 pt boşluk kullanır; GLOBCER şablonu 1,05 aralık, boşluksuz ve
# ilk satırı girintili paragraf ister. Stil dosyası dönüşümden sonra buna
# göre düzeltilir (paragraflarda doğrudan biçimlendirme yok, hepsi stile bağlı).
BODY_SPACING = ('<w:spacing w:lineRule="auto" w:line="252" w:before="0" '
                'w:after="0"/><w:ind w:firstLine="284"/>')
NO_INDENT = '<w:ind w:firstLine="0"/>'


def fix_styles(docx: Path) -> None:
    with zipfile.ZipFile(docx) as zf:
        entries = {n: zf.read(n) for n in zf.namelist()}
    styles = entries["word/styles.xml"].decode()

    def patch(m: re.Match) -> str:
        sid, body = m.group(1), m.group(2)
        if sid == "BodyText":
            body = re.sub(r"<w:spacing[^/]*/>", BODY_SPACING, body)
        elif sid.startswith("GvdeMetni") or sid.startswith("BodyText"):
            # başlık, şekil, tablo notu ve kaynakça satırları girintisiz kalır
            body = body.replace("<w:pPr>", "<w:pPr>" + NO_INDENT, 1)
        return m.group(0).replace(m.group(2), body)

    styles = re.sub(r'<w:style [^>]*w:styleId="([^"]+)"[^>]*>(.*?)</w:style>',
                    patch, styles, flags=re.S)
    entries["word/styles.xml"] = styles.encode()
    with zipfile.ZipFile(docx, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="paper/paper_globcer.tex")
    ap.add_argument("--output", default="paper/paper_globcer.docx")
    args = ap.parse_args()

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("error: LibreOffice (soffice) not found on PATH", file=sys.stderr)
        return 1

    out = Path(args.output)
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        png = tmpdir / "figure2.png"
        figure = png if draw_figure(png) else None
        html_path = tmpdir / (out.stem + ".html")
        html_path.write_text(build_html(Path(args.source).read_text(), figure))
        # HTML'i Writer/Web değil normal Writer belgesi olarak açtırır;
        # docx filtresinin adı açıkça verilmezse dışa aktarma başarısız olur.
        subprocess.run([soffice, "--headless",
                        "-env:UserInstallation=file://" + str(tmpdir / "loprofile"),
                        "--infilter=HTML (StarWriter)",
                        "--convert-to", "docx:MS Word 2007 XML",
                        "--outdir", str(tmpdir), str(html_path)],
                       check=True, capture_output=True)
        produced = tmpdir / (out.stem + ".docx")
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(produced, out)
    fix_styles(out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
