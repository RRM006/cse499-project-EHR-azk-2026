# update_system_flowchart.md — Patient Journey Flowchart (TikZ)

> ⚠️ RECONSTRUCTION NOTE: The original `update_system_flowchart.md` was **not** in the
> uploaded file set, so the source below is a faithful **reconstruction** built from the
> node IDs (S1–S16), style names (GA/DECB/PROC/TERM), loop coordinates (RL1/RL2) and the
> exact add/remove instructions in CONFIRMED CHANGE 1 + CONFIRMED CHANGE 2. It compiles
> standalone. **Diff it against your real file** before committing — node positions and
> exact fill colours are best-effort, not a guaranteed byte-match to your original.

## Module numbering decision
**[ARCHITECT DECISION]** Keep the existing numbers with a **gap at M5** (M6→M15 unchanged),
because ADR-0001…0023 and every cross-reference in nine tracking files already cite
M6–M15 by number, so renumbering would invalidate the entire decision/test trail for zero
functional gain.

```latex
\documentclass[border=12pt]{standalone}
\usepackage{tikz}
\usetikzlibrary{shapes.geometric, arrows.meta, positioning, calc}

\begin{document}
\begin{tikzpicture}[
  node distance = 0.75cm and 0.9cm,
  PROC/.style = {rectangle, rounded corners=2pt, draw=blue!55, fill=blue!8,
                 text width=5.0cm, align=center, minimum height=0.95cm, font=\small},
  DOCS/.style = {rectangle, rounded corners=2pt, draw=green!55!black, fill=green!12,
                 text width=5.0cm, align=center, minimum height=0.95cm, font=\small},
  TERM/.style = {rectangle, rounded corners=11pt, draw=black!55, fill=black!10,
                 text width=4.2cm, align=center, minimum height=0.9cm, font=\small\bfseries},
  DECB/.style = {diamond, aspect=2.1, draw=orange!75!black, fill=yellow!28,
                 align=center, inner sep=1pt, text width=2.7cm, font=\small},
  GA/.style   = {-{Stealth[length=2.6mm]}, thick, draw=black!70},
  LBL/.style  = {font=\small\itshape}
]

% ---------- MAIN VERTICAL FLOW ----------
\node[TERM] (S1)  {START};
\node[PROC, below=of S1]  (S2)  {\textbf{M1} Speech-to-Text (ASR)};
\node[PROC, below=of S2]  (S3)  {\textbf{M2} Text Processing \& Normalisation};
\node[PROC, below=of S3]  (S4)  {\textbf{M3} Information Extraction (NER)};
\node[PROC, below=of S4]  (S5)  {\textbf{M4} Initial Clinical Summary};
% --- M5 (Emergency Detection) intentionally removed: gap kept ---
\node[PROC, below=of S5]  (S6)  {\textbf{M6} Missing Information Analysis};
\node[PROC, below=of S6]  (S7)  {\textbf{M7} Generate Follow-up Questions\\[1pt]
                                  {\scriptsize\itshape (Audio + Text display \textbar{} Voice reply only)}};
\node[PROC, below=of S7]  (S8)  {Patient Answers Verbally};
\node[PROC, below=of S8]  (S9)  {\textbf{M8} Process Response \& Update Profile};
\node[DECB, below=of S9]  (D2)  {\textbf{M9} Profile Complete?};
\node[PROC, below=of D2]  (S10) {\textbf{M10} Risk Assessment\\(Low / Med / High / Critical)};
\node[PROC, below=of S10] (S11) {\textbf{M11} Explainable-AI Risk Driver Report};
\node[PROC, below=of S11] (S12) {\textbf{M12} Generate Clinical Pre-Screening Report};
\node[DOCS, below=of S12] (S13) {\textbf{M13} Store in EHR Database (Encrypted)};
\node[DOCS, below=of S13] (S14) {\textbf{M14} Doctor Reviews on Dashboard};
\node[DOCS, below=of S14] (S15) {\textbf{M15} Doctor Feedback Collected};
\node[TERM, below=of S15] (S16) {END: Consultation Begins};

% ---------- STRAIGHT-THROUGH ARROWS ----------
\draw[GA] (S1)  -- (S2);
\draw[GA] (S2)  -- (S3);
\draw[GA] (S3)  -- (S4);
\draw[GA] (S4)  -- (S5);
\draw[GA] (S5)  -- (S6);                       % <-- M4 now connects DIRECTLY to M6
\draw[GA] (S6)  -- (S7);
\draw[GA] (S7)  -- (S8);
\draw[GA] (S8)  -- (S9);
\draw[GA] (S9)  -- (D2);
\draw[GA] (D2)  -- node[LBL, right=1mm]{Yes} (S10);
\draw[GA] (S10) -- (S11);
\draw[GA] (S11) -- (S12);
\draw[GA] (S12) -- (S13);
\draw[GA] (S13) -- (S14);
\draw[GA] (S14) -- (S15);
\draw[GA] (S15) -- (S16);

% ---------- FOLLOW-UP LOOP (D2 "No" -> back to M7) ----------
\coordinate (RL1) at ($(D2.west)+(-2.6,0)$);
\coordinate (RL2) at ($(S7.west)+(-2.6,0)$);
\draw[GA] (D2.west) -- node[LBL, above]{No} (RL1) -- (RL2) -- (S7.west);

% ---------- LEGEND (Emergency entry removed) ----------
\begin{scope}[shift={($(S5.east)+(3.4,0.4)$)}]
  \node[draw=blue!55,        fill=blue!8,        minimum width=0.55cm, minimum height=0.36cm] (la) {};
  \node[right=1.5mm of la, font=\small] {NLP / ASR modules (M1--M4, M6--M8)};
  \node[draw=orange!75!black,fill=yellow!28, below=2mm of la, minimum width=0.55cm, minimum height=0.36cm] (lb) {};
  \node[right=1.5mm of lb, font=\small] {Follow-up loop (M7--M9)};
  \node[draw=green!55!black, fill=green!12, below=2mm of lb, minimum width=0.55cm, minimum height=0.36cm] (lc) {};
  \node[right=1.5mm of lc, font=\small] {Doctor side (M13--M15)};
\end{scope}

\end{tikzpicture}
\end{document}
```

## Every line changed / added / removed (vs. CONFIRMED CHANGE 1 + 2)
- **Removed** node `D1` (DECA-style diamond, "M5: Emergency Detected?").
- **Removed** node `AX` (ALTB-style box, "ALERT: Escalate to Medical Staff Now").
- **Removed** arrow `\draw[GA] (S5.south)--(D1.north)` (M4 → D1).
- **Removed** arrow `\draw[GA] (D1.south)--node{No}(S6.north)` (D1 "No" → M6).
- **Removed** arrow `\draw[RA] (D1.east)--node{Yes}(AX.west)` (D1 "Yes"/emergency → alert).
- **Removed** arrow `\draw[RA,dashed] (AX.south)...` (dashed parallel-continuation arrow).
- **Added** arrow `\draw[GA] (S5) -- (S6);` (M4 connects directly to M6).
- **Removed** style definition `DECA` (no longer referenced).
- **Removed** style definition `ALTB` (no longer referenced).
- **Removed** arrow style `RA` (only `GA` remains).
- **Added** to S7 node: the subtitle `(Audio + Text display | Voice reply only)` (CONFIRMED CHANGE 2).
- **Updated** legend: deleted the "Emergency" swatch; kept NLP/ASR, Follow-up Loop, Doctor Side.
- **Kept intact:** `D2` diamond, the `No` loop-back via `RL1 → RL2 → S7`, and all other nodes/arrows.
