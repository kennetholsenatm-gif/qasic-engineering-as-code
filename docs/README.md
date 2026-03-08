# Docs

Documentation and whitepapers for **QASIC Engineering-as-Code** ([GitHub](https://github.com/kennetholsenatm-gif/qasic-engineering-as-code)). For quick start and repo layout, see the [main README](../README.md).

## Document index

| Document | Description |
|----------|-------------|
| [APPLICATIONS.md](APPLICATIONS.md) | **Applications:** BQTC (traffic control) and qrnc (quantum-backed tokens, exchange); run instructions and security caveats |
| [Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.tex](Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.tex) | **Unified whitepaper (LaTeX):** EaC for Quantum ASICs; protocol, simulation, routing, applications |
| [Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md](Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md) | (Unified; see .tex for canonical source) |
| [architecture_overview.md](architecture_overview.md) | Full-stack diagram: protocol layer → routing → inverse design → hardware → applications |
| [QUANTUM_ASIC.md](QUANTUM_ASIC.md) | Quantum ASIC spec: minimal topology (0–1–2), gate set (H, X, Z, CNOT), protocol mapping |
| [WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md](WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md) | Main whitepaper (Markdown): vision, protocol layer, roadmap, §10 supporting code |
| [WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex](WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex) | Short LaTeX paper + math appendix (QAOA, DNN phase synthesis) |
| [Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md](Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md) | **Markdown:** Cryogenic metamaterials, rf-SQUIDs, BAW, Cryo-CMOS, SATCOM (GitHub-friendly) |
| [Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.tex](Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.tex) | Full LaTeX report |
| [Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md](Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md) | **Markdown:** Code-based materials science, simulation stack (GitHub-friendly) |
| [Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.tex](Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.tex) | Full LaTeX report |
| [Engineering_as_Code_Distributed_Computational_Roadmap.md](Engineering_as_Code_Distributed_Computational_Roadmap.md) | **Markdown:** EaC distributed roadmap (GitHub-friendly) |
| [Engineering_as_Code_Distributed_Computational_Roadmap.tex](Engineering_as_Code_Distributed_Computational_Roadmap.tex) | Full LaTeX report |
| [quantum-terrestrial-backhaul.md](quantum-terrestrial-backhaul.md) | **Markdown:** Quantum-secured terrestrial P2P backhaul, metamaterials, QI, radiative cooling (GitHub-friendly) |
| [quantum-terrestrial-backhaul.tex](quantum-terrestrial-backhaul.tex) | Full LaTeX report |

**How to read:** Each whitepaper has a **Markdown (.md)** version for GitHub and quick reading; the **LaTeX (.tex)** source is for full equations and PDF build. For vision and protocols → [WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md](WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md). For EaC roadmap, cryogenic metamaterials, computational materials science, and terrestrial backhaul → use the corresponding .md files above. See the main [README](../README.md) for repo layout.

### Building PDFs (TeX Live)

All LaTeX sources are intended to be compiled with **XeLaTeX** (Noto Sans, Unicode). The documents use `babel` with `bidi=bidi` for XeLaTeX compatibility (do not use `bidi=basic`, which is LuaTeX-only). With [TeX Live](https://tug.org/texlive/) installed and `xelatex` on your PATH (if you just installed TeX Live, open a new terminal or add TeX Live’s `bin` folder to PATH, e.g. `C:\texlive\2024\bin\windows`):

- **From repo root:**  
  `.\docs\build_pdfs.ps1`  
  This builds all LaTeX PDFs (two passes each for references) and writes them in `docs/`.
- **Manual (from `docs/`):**  
  `xelatex WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex` (run twice), then the same for `Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.tex`.
