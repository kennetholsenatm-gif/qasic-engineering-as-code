"""
CLI dashboard for QASIC Engineering-as-Code.
Menu to run protocol (sim/hardware), routing, pipeline, inverse design;
view last results; show doc links. Uses Rich for output.
Run from repo root: python -m dashboard  or  python dashboard/cli_dashboard.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINEERING_DIR = REPO_ROOT / "engineering"
DOCS_DIR = REPO_ROOT / "docs"

# Default pipeline output base name (must match run_pipeline.py default)
PIPELINE_BASE = "pipeline_result"
ROUTING_JSON = ENGINEERING_DIR / f"{PIPELINE_BASE}_routing.json"
INVERSE_JSON = ENGINEERING_DIR / f"{PIPELINE_BASE}_inverse.json"
PHASES_NPY = ENGINEERING_DIR / f"{PIPELINE_BASE}_inverse_phases.npy"


def _run(cmd: list[str], cwd: Path | None = None) -> int:
    """Run command; return exit code. cwd defaults to repo root."""
    return subprocess.run(cmd, cwd=cwd or REPO_ROOT).returncode


def run_protocol_sim() -> None:
    _run([sys.executable, str(ENGINEERING_DIR / "run_protocol_on_ibm.py"), "--protocol", "teleport"])


def run_protocol_hardware() -> None:
    _run([sys.executable, str(ENGINEERING_DIR / "run_protocol_on_ibm.py"), "--protocol", "teleport", "--hardware"])


def run_routing_sim() -> None:
    _run([
        sys.executable,
        str(ENGINEERING_DIR / "routing_qubo_qaoa.py"),
        "-o", str(ENGINEERING_DIR / "dashboard_routing.json"),
    ])


def run_routing_hardware_fast() -> None:
    _run([
        sys.executable,
        str(ENGINEERING_DIR / "routing_qubo_qaoa.py"),
        "--hardware", "--fast",
        "-o", str(ENGINEERING_DIR / "dashboard_routing.json"),
    ])


def run_pipeline_sim() -> None:
    _run([sys.executable, str(ENGINEERING_DIR / "run_pipeline.py")])


def run_inverse_design() -> None:
    cmd = [sys.executable, str(ENGINEERING_DIR / "metasurface_inverse_net.py"), "-o", str(ENGINEERING_DIR / "dashboard_inverse.json")]
    if ROUTING_JSON.exists():
        cmd.extend(["--routing-result", str(ROUTING_JSON)])
    _run(cmd)


def view_last_results(console: "Console | None" = None) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    if console is None:
        console = Console()

    # Prefer pipeline_result; fall back to dashboard_* if present
    rj = ROUTING_JSON if ROUTING_JSON.exists() else (ENGINEERING_DIR / "dashboard_routing.json")
    ij = INVERSE_JSON if INVERSE_JSON.exists() else (ENGINEERING_DIR / "dashboard_inverse.json")
    if not rj.exists() and not ij.exists():
        console.print(Panel("[yellow]No results yet.[/yellow] Run pipeline or routing + inverse first.", title="Last results"))
        return

    parts = []
    if rj.exists():
        try:
            with open(rj, encoding="utf-8") as f:
                data = json.load(f)
            tbl = Table(title="Routing")
            tbl.add_column("Key", style="cyan")
            tbl.add_column("Value", style="green")
            tbl.add_row("solver", str(data.get("solver", "—")))
            tbl.add_row("objective", str(data.get("objective_value", "—")))
            tbl.add_row("backend", str(data.get("backend", "—")))
            mapping = data.get("mapping", [])
            for m in mapping:
                tbl.add_row(f"logical {m.get('logical')} -> physical", str(m.get("physical", "—")))
            parts.append(Panel(tbl, title="Routing result"))
        except (OSError, json.JSONDecodeError) as e:
            parts.append(Panel(f"[red]Error reading routing JSON: {e}[/red]", title="Routing"))

    if ij.exists():
        try:
            with open(ij, encoding="utf-8") as f:
                data = json.load(f)
            tbl = Table(title="Inverse design")
            tbl.add_column("Key", style="cyan")
            tbl.add_column("Value", style="green")
            tbl.add_row("phase_min", str(data.get("phase_min", "—")))
            tbl.add_row("phase_max", str(data.get("phase_max", "—")))
            tbl.add_row("phase_mean", str(data.get("phase_mean", "—")))
            tbl.add_row("num_meta_atoms", str(data.get("num_meta_atoms", "—")))
            parts.append(Panel(tbl, title="Inverse result"))
        except (OSError, json.JSONDecodeError) as e:
            parts.append(Panel(f"[red]Error reading inverse JSON: {e}[/red]", title="Inverse"))

    for p in parts:
        console.print(p)


def run_bqtc_one_cycle(console: "Console | None" = None) -> None:
    """Run one BQTC pipeline cycle (no live telemetry)."""
    from rich.console import Console
    if console is None:
        console = Console()
    bqtc_dir = REPO_ROOT / "apps" / "bqtc"
    script = bqtc_dir / "run_one_cycle.py"
    if not script.is_file():
        console.print("[yellow]BQTC run_one_cycle.py not found. See apps/README.md.[/yellow]")
        return
    code = _run([sys.executable, str(script)], cwd=bqtc_dir)
    if code != 0:
        console.print("[red]BQTC run-one-cycle failed.[/red]")
    else:
        console.print("[green]BQTC one cycle completed.[/green] (See apps/README.md for full pipeline.)")


def run_qrnc_demo(console: "Console | None" = None) -> None:
    """Mint two QRNC tokens and run two-party exchange (sim)."""
    from rich.console import Console
    from rich.panel import Panel
    if console is None:
        console = Console()
    try:
        from apps.qrnc import mint_qrnc, run_two_party_exchange
    except Exception as e:
        console.print(Panel(f"[red]QRNC import failed: {e}[/red]\nEnsure QRNG.PY is at repo root. See apps/README.md.", title="QRNC"))
        return
    try:
        console.print("Minting two tokens (simulator)...")
        t_a = mint_qrnc(32, use_real_hardware=False)
        t_b = mint_qrnc(32, use_real_hardware=False)
        rec_a, rec_b, record = run_two_party_exchange(t_a, t_b, party_a_id="Alice", party_b_id="Bob")
        if rec_a is None:
            console.print(Panel("[red]Exchange verification failed.[/red]", title="QRNC"))
            return
        console.print(Panel(
            f"Exchange succeeded.\nAlice received: {rec_a.value[:16]}...\nBob received: {rec_b.value[:16]}...",
            title="QRNC",
        ))
    except Exception as e:
        console.print(Panel(f"[red]{e}[/red]", title="QRNC"))


def show_doc_links(console: "Console | None" = None, open_browser: bool = False) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    if console is None:
        console = Console()

    links: list[tuple[str, Path]] = [
        ("Architecture overview", DOCS_DIR / "architecture_overview.md"),
        ("Quantum ASIC spec", DOCS_DIR / "QUANTUM_ASIC.md"),
        ("Whitepaper (Markdown)", DOCS_DIR / "WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md"),
        ("Docs index", DOCS_DIR / "README.md"),
        ("Engineering README", ENGINEERING_DIR / "README.md"),
        ("Applications (BQTC, QRNC)", DOCS_DIR / "APPLICATIONS.md"),
        ("Apps README", REPO_ROOT / "apps" / "README.md"),
    ]
    tbl = Table(title="Documentation")
    tbl.add_column("Document", style="cyan")
    tbl.add_column("Path", style="green")
    for name, path in links:
        if path.exists():
            try:
                p = path.relative_to(REPO_ROOT)
            except ValueError:
                p = path
        else:
            p = path
        tbl.add_row(name, str(p))
    console.print(Panel(tbl, title="Docs"))
    if open_browser:
        for _name, path in links:
            if path.exists():
                webbrowser.open(path.as_uri())
                break


def main() -> int:
    try:
        from rich.console import Console
        from rich.panel import Panel
    except ImportError:
        print("Install rich: pip install rich", file=sys.stderr)
        return 1

    if not getattr(sys.stdin, "isatty", lambda: False)():
        print("CLI dashboard requires an interactive terminal.", file=sys.stderr)
        print("Run from a terminal: python -m dashboard", file=sys.stderr)
        return 1

    console = Console()
    os.chdir(REPO_ROOT)

    while True:
        console.print(Panel(
            "[bold]QASIC Engineering-as-Code[/bold] – CLI Dashboard\n\n"
            "  [1] Run protocol (sim)\n"
            "  [2] Run protocol (IBM hardware)\n"
            "  [3] Run routing (sim)\n"
            "  [4] Run routing (IBM, fast)\n"
            "  [5] Run full pipeline (sim)\n"
            "  [6] Run inverse design\n"
            "  [7] View last results\n"
            "  [8] Show doc links\n"
            "  [9] Run BQTC pipeline (one cycle)\n"
            "  [10] Quantum tokens (QRNC): mint and exchange demo\n"
            "  [11] Quit",
            title="Menu",
        ))
        try:
            print("Choice [1-11] (default 11): ", end="", flush=True)
            raw = input().strip() or "11"
            choice = int(raw)
        except (ValueError, KeyboardInterrupt, EOFError):
            choice = 11

        if choice == 1:
            run_protocol_sim()
        elif choice == 2:
            run_protocol_hardware()
        elif choice == 3:
            run_routing_sim()
        elif choice == 4:
            run_routing_hardware_fast()
        elif choice == 5:
            run_pipeline_sim()
        elif choice == 6:
            run_inverse_design()
        elif choice == 7:
            view_last_results(console)
        elif choice == 8:
            show_doc_links(console, open_browser=False)
        elif choice == 9:
            run_bqtc_one_cycle(console)
        elif choice == 10:
            run_qrnc_demo(console)
        elif choice == 11:
            return 0
        else:
            console.print("[yellow]Invalid choice.[/yellow]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
