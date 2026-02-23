"""
Command-line interface for photo_cleaner.

Provides CLI commands for indexing, analysis, and reporting.
"""

import logging
import sys
from pathlib import Path

import click

from photo_cleaner.core.indexer import PhotoIndexer
from photo_cleaner.db.schema import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / ".photo_cleaner" / "photo_cleaner.db"


@click.group()
@click.option(
    "--db",
    "db_path",
    type=click.Path(path_type=Path),
    default=DEFAULT_DB_PATH,
    help="Path to SQLite database",
)
@click.pass_context
def cli(ctx: click.Context, db_path: Path) -> None:
    """Photo Cleaner - Local photo collection analyzer."""
    ctx.ensure_object(dict)

    # Ensure database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    ctx.obj["db_path"] = db_path
    logger.debug(f"Using database: {db_path}")


@cli.command()
@click.argument("folder", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--skip-existing/--reindex",
    default=True,
    help="Skip already indexed files",
)
@click.option(
    "--workers",
    type=int,
    default=None,
    help="Number of parallel workers",
)
@click.pass_context
def index(ctx: click.Context, folder: Path, skip_existing: bool, workers: int) -> None:
    """
    Index photos in FOLDER recursively.

    Scans the folder for image files, computes hashes,
    and stores metadata in the database.
    """
    db_path = ctx.obj["db_path"]
    click.echo(f"Indexing folder: {folder}")
    click.echo(f"Database: {db_path}")

    with Database(db_path) as db:
        indexer = PhotoIndexer(db, max_workers=workers)
        stats = indexer.index_folder(folder, skip_existing=skip_existing)

        click.echo("\n" + "=" * 50)
        click.echo("Indexing Results:")
        click.echo(f"  ✓ Processed: {stats['processed']}")
        click.echo(f"  ⊘ Skipped:   {stats['skipped']}")
        click.echo(f"  ✗ Failed:    {stats['failed']}")
        click.echo("=" * 50)


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Display database statistics."""
    db_path = ctx.obj["db_path"]

    if not db_path.exists():
        click.echo(f"Database not found: {db_path}", err=True)
        click.echo("Run 'photo-cleaner index <folder>' first", err=True)
        sys.exit(1)

    with Database(db_path) as db:
        indexer = PhotoIndexer(db)
        db_stats = indexer.get_stats()

        click.echo("\n" + "=" * 50)
        click.echo("Photo Cleaner Statistics")
        click.echo("=" * 50)
        click.echo(f"Database: {db_path}")
        click.echo(f"Total indexed files: {db_stats['total_files']}")
        click.echo("=" * 50)


def main() -> None:
    """Entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()