# Build LaTeX PDFs with XeLaTeX (requires TeX Live or MiKTeX).
# Run from repo root: .\docs\build_pdfs.ps1
# Or from docs: .\build_pdfs.ps1
# PDFs are written next to the .tex files in docs/.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $scriptDir

$texFiles = @(
    "Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.tex",
    "WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex",
    "Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.tex",
    "Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.tex",
    "Engineering_as_Code_Distributed_Computational_Roadmap.tex"
)

foreach ($tex in $texFiles) {
    if (-not (Test-Path $tex)) {
        Write-Warning "Skip (not found): $tex"
        continue
    }
    $base = [System.IO.Path]::GetFileNameWithoutExtension($tex)
    Write-Host "Building $base ..."
    foreach ($pass in 1..2) {
        & xelatex -interaction=nonstopmode -halt-on-error $tex 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Error "xelatex failed for $tex (pass $pass). Run manually: xelatex $tex"
            Pop-Location
            exit $LASTEXITCODE
        }
    }
    Write-Host "  -> $base.pdf"
}

Pop-Location
Write-Host "Done. PDFs are in docs/."
