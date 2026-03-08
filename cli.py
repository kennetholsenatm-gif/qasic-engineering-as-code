"""
Unified CLI for QASIC Engineering-as-Code.
Usage:
  qasic run-pipeline [--config CONFIG]
  qasic view-results [--job-id JOB_ID]
  qasic serve [--host HOST] [--port PORT]
  qasic project create NAME [--description DESC]
  qasic project list
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import typer
except ImportError:
    print("Install typer: pip install typer", file=sys.stderr)
    sys.exit(1)

cli = typer.Typer(help="QASIC Engineering-as-Code CLI")


@cli.command()
def run_pipeline(
    config: Path = typer.Option(None, "--config", "-c", help="YAML config (pipeline section). Default: config/pipeline_config.yaml"),
    output_base: str = typer.Option("pipeline_result", "--output", "-o", help="Output base name"),
    fast: bool = typer.Option(False, "--fast", help="Fast routing/inverse"),
    routing_method: str = typer.Option("qaoa", "--routing-method", help="qaoa or rl"),
    model: str = typer.Option("mlp", "--model", help="mlp or gnn"),
    heac: bool = typer.Option(False, "--heac", help="Run HEaC (phases -> geometry -> GDS)"),
    skip_routing: bool = typer.Option(False, "--skip-routing"),
    skip_inverse: bool = typer.Option(False, "--skip-inverse"),
):
    """Run the full pipeline (routing + inverse design)."""
    cfg_path = config or REPO_ROOT / "config" / "pipeline_config.yaml"
    if config and not cfg_path.is_file():
        typer.echo(f"Config not found: {cfg_path}", err=True)
        raise typer.Exit(1)
    engineering_dir = REPO_ROOT / "engineering"
    run_script = engineering_dir / "run_pipeline.py"
    if not run_script.is_file():
        typer.echo("engineering/run_pipeline.py not found.", err=True)
        raise typer.Exit(1)
    cmd = [sys.executable, str(run_script), "-o", output_base]
    if fast:
        cmd.append("--fast")
    if routing_method in ("qaoa", "rl"):
        cmd.extend(["--routing-method", routing_method])
    if model in ("mlp", "gnn"):
        cmd.extend(["--model", model])
    if heac:
        cmd.append("--heac")
    if skip_routing:
        cmd.append("--skip-routing")
    if skip_inverse:
        cmd.append("--skip-inverse")
    typer.echo("Running: " + " ".join(cmd))
    import subprocess
    r = subprocess.run(cmd, cwd=REPO_ROOT)
    if r.returncode != 0:
        raise typer.Exit(r.returncode)


@cli.command()
def view_results(
    job_id: str = typer.Option(None, "--job-id", help="Celery task ID to check (optional)"),
    project_id: int = typer.Option(None, "--project-id", help="Project ID to show latest run for"),
):
    """Show latest pipeline results or status of a job."""
    if job_id:
        try:
            import urllib.request
            import urllib.error
            import json as _json
            base = os.environ.get("QASIC_API_BASE", "http://localhost:8000")
            req = urllib.request.Request(f"{base}/api/tasks/{job_id}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode())
            typer.echo(f"Task {job_id}: {data.get('status', 'unknown')}")
            if data.get("result"):
                typer.echo(f"Result: {data['result']}")
            if data.get("error"):
                typer.echo(f"Error: {data['error']}")
        except urllib.error.URLError as e:
            typer.echo(f"Cannot reach API: {e}. Set QASIC_API_BASE or run 'qasic serve' first.", err=True)
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
        return
    try:
        from storage.db import get_latest_pipeline_run, list_projects, is_enabled
        if is_enabled() and project_id is not None:
            row = get_latest_pipeline_run(project_id=project_id)
        elif is_enabled():
            row = get_latest_pipeline_run()
        else:
            row = None
        if not row:
            typer.echo("No pipeline runs found. Run: qasic run-pipeline")
            return
        typer.echo(f"Run id: {row.get('id')}  status: {row.get('status')}")
        typer.echo(f"  routing:  {row.get('routing_path') or '-'}")
        typer.echo(f"  inverse:  {row.get('inverse_path') or '-'}")
        typer.echo(f"  GDS:      {row.get('gds_path') or '-'}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@cli.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code change"),
):
    """Start the FastAPI web app (uvicorn)."""
    try:
        import uvicorn
    except ImportError:
        typer.echo("Install uvicorn: pip install 'uvicorn[standard]'", err=True)
        raise typer.Exit(1)
    typer.echo(f"Starting API at http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


project_app = typer.Typer(help="Project-based workspace")
cli.add_typer(project_app, name="project")


@project_app.command("create")
def project_create(
    name: str = typer.Argument(..., help="Project name"),
    description: str = typer.Option("", "--description", "-d"),
):
    """Create a new project."""
    try:
        from storage.db import create_project, get_project, is_enabled
        if not is_enabled():
            typer.echo("Database not configured (set DATABASE_URL).", err=True)
            raise typer.Exit(1)
        pid = create_project(name, description or None)
        if pid is None:
            typer.echo("Failed (name may already exist).", err=True)
            raise typer.Exit(1)
        proj = get_project(pid)
        typer.echo(f"Created project id={pid} name={proj.get('name', name)}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@project_app.command("list")
def project_list():
    """List all projects."""
    try:
        from storage.db import list_projects, is_enabled
        if not is_enabled():
            typer.echo("Database not configured (set DATABASE_URL).")
            return
        projects = list_projects()
        for p in projects:
            typer.echo(f"  {p['id']}  {p['name']}  {p.get('description', '')[:50]}")
        if not projects:
            typer.echo("No projects yet. Create one: qasic project create 'My Project'")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    cli()
