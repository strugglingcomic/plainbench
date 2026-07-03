"""PlainBench command-line interface."""

import click

from plainbench.__version__ import __version__
from plainbench.analysis import compare_runs
from plainbench.comparison import _render_table, format_time
from plainbench.config.settings import BenchmarkConfig
from plainbench.storage.database import BenchmarkDatabase


def _open_database(path: str) -> BenchmarkDatabase:
    db = BenchmarkDatabase(path)
    db.initialize()
    return db


database_option = click.option(
    "--database",
    "-d",
    default=None,
    envvar="PLAINBENCH_DATABASE",
    help="Path to the benchmark database (default: ./benchmarks.db).",
)


@click.group()
@click.version_option(version=__version__, prog_name="plainbench")
def cli():
    """PlainBench: simple, local-first benchmarking and comparison."""


@cli.command()
@database_option
@click.option("--limit", "-n", default=10, help="Number of runs to list.")
def runs(database, limit):
    """List recent benchmark runs stored in the database."""
    db = _open_database(database or BenchmarkConfig.get_default_database())
    try:
        all_runs = db.get_all_runs()[:limit]
        if not all_runs:
            click.echo("No benchmark runs found.")
            return

        rows = []
        for run in all_runs:
            names = sorted(db.get_run_wall_times(run.run_id))
            rows.append(
                [
                    str(run.run_id),
                    run.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    ", ".join(names) or "-",
                ]
            )
        click.echo(_render_table(["run", "timestamp", "benchmarks"], rows))
    finally:
        db.close()


@cli.command()
@database_option
@click.option("--run-id", type=int, default=None, help="Run to show (default: latest).")
def show(database, run_id):
    """Show timing statistics for a stored run."""
    import statistics as st

    db = _open_database(database or BenchmarkConfig.get_default_database())
    try:
        if run_id is None:
            latest = db.get_latest_run()
            if latest is None:
                click.echo("No benchmark runs found.")
                return
            run_id = latest.run_id

        wall_times = db.get_run_wall_times(run_id)
        if not wall_times:
            click.echo(f"No measurements found for run {run_id}.")
            return

        rows = []
        for name, times in sorted(wall_times.items()):
            stddev = st.stdev(times) if len(times) > 1 else 0.0
            rows.append(
                [
                    name,
                    str(len(times)),
                    format_time(st.fmean(times)),
                    format_time(stddev),
                    format_time(min(times)),
                    format_time(max(times)),
                ]
            )
        click.echo(f"Run {run_id}")
        click.echo(_render_table(["benchmark", "n", "mean", "stddev", "min", "max"], rows))
    finally:
        db.close()


@cli.command()
@database_option
@click.argument("baseline", type=int)
@click.argument("current", type=int)
@click.option("--threshold", default=0.05, help="Regression threshold (0.05 = 5%).")
def compare(database, baseline, current, threshold):
    """Compare two stored runs by run id (BASELINE vs CURRENT)."""
    db_path = database or BenchmarkConfig.get_default_database()
    comparisons = compare_runs(db_path, baseline, current)
    if not comparisons:
        click.echo(f"No benchmarks in common between runs {baseline} and {current}.")
        raise SystemExit(1)

    rows = []
    regressions = 0
    for c in comparisons:
        if c.is_regression(threshold):
            verdict = "REGRESSION"
            regressions += 1
        elif c.is_improvement(threshold):
            verdict = "improvement"
        else:
            verdict = "~unchanged"
        rows.append(
            [
                c.benchmark_name,
                format_time(c.baseline_mean),
                format_time(c.current_mean),
                f"{c.change:+.1%}",
                verdict,
            ]
        )
    click.echo(_render_table(["benchmark", "baseline", "current", "change", "verdict"], rows))
    if regressions:
        click.echo(f"\n{regressions} regression(s) detected.")
        raise SystemExit(1)


@cli.command()
def demo():
    """Run the flagship demo: 3 designs x 3 infrastructure profiles."""
    from plainbench.demo import main

    main()


if __name__ == "__main__":
    cli()
