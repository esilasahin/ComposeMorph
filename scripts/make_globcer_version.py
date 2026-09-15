#!/usr/bin/env python3
"""Generate the GLOBCER'26 single-column variant of the paper.

paper/paper.tex is the source of record (IEEEtran, two columns). GLOBCER's
template is a single-column Word layout: A4, Times New Roman 12pt, the
abstract as a bold run-in paragraph, Roman section numbers, table captions
above and figure captions below, tables numbered with Roman numerals.

This script re-wraps the same body text in that layout, so the two
versions cannot drift apart: edit paper/paper.tex, re-run this, done.

Usage:
    python3 scripts/make_globcer_version.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TR_UPPER = str.maketrans("iıçğöşü", "İIÇĞÖŞÜ")


def tr_upper(s: str) -> str:
    # Türkçe büyük harf: i -> İ. "Round-Trip" İngilizce bir terim olduğundan
    # noktasız I ile yazılır.
    return s.translate(TR_UPPER).upper().replace("TRİP", "TRIP")


PREAMBLE = r"""% GENERATED FILE -- do not edit by hand.
% Source: paper/paper.tex; regenerate with scripts/make_globcer_version.py
% Layout: GLOBCER'26 full-paper template (single column, A4, Times 12pt).
\documentclass[12pt,a4paper]{article}

\usepackage{iftex}
\ifPDFTeX
  \usepackage[utf8]{inputenc}
  \usepackage[T1]{fontenc}
  \usepackage{newtxtext,newtxmath}
\else
  \usepackage{fontspec}
  \setmainfont{texgyretermes}[Extension=.otf, UprightFont=*-regular,
    BoldFont=*-bold, ItalicFont=*-italic, BoldItalicFont=*-bolditalic]
  \setmonofont{texgyrecursor}[Extension=.otf, UprightFont=*-regular,
    BoldFont=*-bold, ItalicFont=*-italic, BoldItalicFont=*-bolditalic]
\fi
\usepackage[english,turkish,shorthands=off]{babel}
\usepackage[a4paper,top=3cm,bottom=2.5cm,left=2.5cm,right=2.5cm]{geometry}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{caption}
\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepgfplotslibrary{groupplots}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{booktabs}
\usepackage[hyphens]{url}
\usepackage[hidelinks]{hyperref}

% Şablondaki başlık düzeni: I. BÖLÜM ADI / A. Alt bölüm adı
\renewcommand{\thesection}{\Roman{section}.}
\renewcommand{\thesubsection}{\Alph{subsection}.}
\titleformat{\section}{\normalsize\bfseries}{\thesection}{0.5em}{}
\titleformat{\subsection}{\normalsize\itshape}{\thesubsection}{0.5em}{}
\titlespacing*{\section}{0pt}{12pt}{6pt}
\titlespacing*{\subsection}{0pt}{10pt}{4pt}

% Tablolar Roma rakamıyla numaralanır; tablo başlığı üstte, şekil başlığı altta.
\renewcommand{\thetable}{\Roman{table}}
\captionsetup{font=small, labelsep=period}
\captionsetup[figure]{name=Şekil, justification=centering}
\captionsetup[table]{name=Tablo, justification=centering}
\renewcommand{\refname}{KAYNAKLAR}

\fancypagestyle{globcerfirst}{%
  \fancyhf{}%
  \fancyhead[R]{\textbf{GLOBCER'26, 14-17 October 2026}}%
  \renewcommand{\headrulewidth}{0.8pt}%
}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[C]{\itshape 6\textsuperscript{th} Global Conference on Engineering
Research (GLOBCER'26)}
\renewcommand{\headrulewidth}{0pt}

\setlength{\parindent}{1.2em}
% 12 pt tek sütunda uzun kod adları satır sonuna sığmayabiliyor; kod
% adlarını tireyle bölmek yerine satır aralıklarına esneklik tanınır.
\setlength{\emergencystretch}{3em}
\sloppy

\begin{document}
\thispagestyle{globcerfirst}

\begin{center}
{\large\bfseries C++ Ortamında Konteyner Servis Yapılandırmalarının
Güvenli Round-Trip Düzenlenmesi\par}
\smallskip
{\itshape Safe Round-Trip Editing of Container Service Configurations in C++\par}
\end{center}

\noindent\rule{\textwidth}{0.4pt}
\begin{center}
Esila Şahin\textsuperscript{*,1}, Ömer Yıldız\textsuperscript{2},
Mehmet Berk Kartal\textsuperscript{3}, Ahmet Batuhan Canlı\textsuperscript{4}
\ (\textsuperscript{*}: \textit{sorumlu yazar})
\end{center}
\noindent\rule{\textwidth}{0.4pt}

\begin{center}\small
\textsuperscript{*}esila.sahin@stu.fsm.edu.tr, ORCID: 0009-0007-8858-9540\\
\textsuperscript{1}\textit{Yazılım Mühendisliği Bölümü, Fatih Sultan Mehmet
Vakıf Üniversitesi, İstanbul, Türkiye}\\
\textsuperscript{2,3,4}\textit{TÜBİTAK BİLGEM UEKAE, Kocaeli, Türkiye}
\end{center}

\bigskip

"""

FOOTER = "\n\\end{document}\n"

TR_KEYWORDS = ("Docker Compose, YAML Round-Trip Düzenleme, Kod Olarak "
               "Yapılandırma, Yapı Koruma, C++")
EN_KEYWORDS = ("Docker Compose, YAML Round-Trip Editing, Configuration As "
               "Code, Structure Preservation, C++")


def extract(src: str, start: str, end: str) -> str:
    return src.split(start, 1)[1].split(end, 1)[0].strip()


def build(src: str) -> str:
    tr_abstract = extract(src, r"\begin{abstract}", r"\end{abstract}")
    en_abstract = extract(src, r"\begin{otherlanguage}{english}", r"\end{abstract}")
    en_abstract = extract(en_abstract + r"\end{abstract}", r"\begin{abstract}",
                          r"\end{abstract}")

    body = src.split(r"\section{Giriş}", 1)[1]
    body = r"\section{Giriş}" + body.split(r"\end{document}", 1)[0]

    # IEEEtran'a özgü komut; article sınıfında karşılığı yok.
    body = re.sub(r"^%.*\n", "", body, flags=re.M)
    body = body.replace(r"\IEEEtriggeratref{13}", "")

    # Tek sütun: yayılan şekil ortamına gerek yok, grafik biraz daralır.
    body = body.replace(r"\begin{figure*}", r"\begin{figure}")
    body = body.replace(r"\end{figure*}", r"\end{figure}")
    body = body.replace("width=0.44\\textwidth, height=4.4cm",
                        "width=0.40\\textwidth, height=4.6cm")
    body = body.replace("horizontal sep=1.8cm", "horizontal sep=1.3cm")
    body = body.replace("\\footnotesize\n\\setlength{\\tabcolsep}{3pt}",
                        "\\small\n\\setlength{\\tabcolsep}{6pt}")

    # Bölüm başlıkları şablondaki gibi büyük harfle (Türkçe kurallarına göre).
    body = re.sub(r"\\section\{([^}]*)\}",
                  lambda m: "\\section{" + tr_upper(m.group(1)) + "}", body)

    front = (
        "\\noindent\\textbf{Özet} " + tr_abstract + "\n\n"
        "\\smallskip\\noindent\\textbf{\\textit{Anahtar Kelimeler:}} "
        "\\textit{" + TR_KEYWORDS + "}\n\n"
        "\\bigskip\n\n"
        "\\noindent\\textbf{Abstract} " + en_abstract + "\n\n"
        "\\smallskip\\noindent\\textbf{\\textit{Keywords:}} "
        "\\textit{" + EN_KEYWORDS + "}\n\n"
        "\\bigskip\n\n"
    )
    return PREAMBLE + front + body + FOOTER


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="paper/paper.tex")
    ap.add_argument("--output", default="paper/paper_globcer.tex")
    args = ap.parse_args()
    out = Path(args.output)
    out.write_text(build(Path(args.source).read_text()))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
