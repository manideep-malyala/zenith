"""Command-line interface for ZENITH.

Provides CLI commands for scanning local repositories and remote GitHub URLs
to produce deterministic, multi-metric Evidence Packages.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path

from src.core.logging import logger, setup_logger
from src.pipeline.orchestrator import ScanPipeline

__version__ = "1.0.0"


def is_git_url(target: str) -> bool:
    """Checks whether the given target string is a remote Git/GitHub URL.

    Args:
        target: Filepath or URL to check.

    Returns:
        bool: True if target resembles a git/http repository URL, False otherwise.
    """
    target_lower = target.lower()
    return target_lower.startswith(("http://", "https://", "git@", "github.com/"))


def clone_repo(url: str, dest_dir: Path) -> bool:
    """Clones a remote git repository using shallow depth into a destination directory.

    Args:
        url: Remote repository URL.
        dest_dir: Local destination path for cloning.

    Returns:
        bool: True if clone succeeded, False otherwise.
    """
    if url.startswith("github.com/"):
        url = f"https://{url}"
    logger.info(f"Cloning repository: {url} ...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--", url, str(dest_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error cloning repository: {e.stderr}")
        return False


def create_parser() -> argparse.ArgumentParser:
    """Constructs the top-level argument parser for zenith.

    Returns:
        argparse.ArgumentParser: Configured parser with commands and options.
    """
    parser = argparse.ArgumentParser(
        prog="zenith",
        description="Deterministic static analysis & semantic graph repository intelligence engine.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug logging.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress informational output, showing only errors and warnings.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # version command
    subparsers.add_parser("version", help="Show version and exit.")

    # scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a target repository (local path or GitHub URL) and produce an Evidence Package.",
    )
    scan_parser.add_argument("target", help="Path or GitHub URL of the repository to analyze.")
    scan_parser.add_argument(
        "output_pos",
        nargs="?",
        default=None,
        help="Optional output directory (positional alternative to --output)",
    )
    scan_parser.add_argument(
        "--output",
        "-o",
        default="scan-output",
        help="Directory to write metadata.json, knowledge.json, and top_learnings.json (default: ./scan-output)",
    )
    scan_parser.add_argument(
        "--mode",
        "-m",
        choices=["fast", "standard", "deep"],
        default="standard",
        help="Analysis mode (fast: skip betweenness; standard: full graph; deep: exhaustive metrics)",
    )
    scan_parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=None,
        help="Number of worker threads for parallel AST parsing (default: auto)",
    )
    scan_parser.add_argument(
        "--catalog",
        default=None,
        help="Custom path to capabilities.yaml catalog file",
    )
    scan_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug logging.",
    )
    scan_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress informational output, showing only errors and warnings.",
    )

    return parser


def main(args: Sequence[str] | None = None) -> None:
    """Main CLI execution handler.

    Args:
        args: Optional list of command line argument strings. If None, uses sys.argv[1:].
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    setup_logger(verbose=parsed_args.verbose, quiet=parsed_args.quiet)

    if not parsed_args.command:
        parser.print_help()
        sys.exit(1)

    if parsed_args.command == "version":
        print(f"zenith {__version__}")
        sys.exit(0)

    if parsed_args.command == "scan":
        target = parsed_args.target
        output_dir = parsed_args.output_pos if parsed_args.output_pos else parsed_args.output

        is_remote = is_git_url(target)
        temp_clone_dir = None

        if is_remote:
            temp_clone_dir = Path(tempfile.mkdtemp(prefix="zenith_clone_"))
            success = clone_repo(target, temp_clone_dir)
            if not success:
                shutil.rmtree(temp_clone_dir, ignore_errors=True)
                sys.exit(1)
            scan_target = temp_clone_dir
        else:
            scan_target = Path(target)
            if not scan_target.exists():
                logger.error(f"Target path '{scan_target}' does not exist.")
                sys.exit(1)

        try:
            logger.info(f"Starting ZENITH scan on: {scan_target.resolve()}")
            t0 = time.time()

            pipeline = ScanPipeline(
                target_dir=scan_target,
                catalog_file=parsed_args.catalog,
                workers=parsed_args.workers,
                mode=parsed_args.mode,
            )

            pipeline.run(output_dir=output_dir)
            elapsed = time.time() - t0

            out_resolved = Path(output_dir).resolve()
            logger.info(f"Scan complete in {elapsed:.2f}s!")
            logger.info(f"Evidence Package written to: {out_resolved}/")
            logger.info("   |-- metadata.json")
            logger.info("   |-- knowledge.json")
            logger.info("   +-- top_learnings.json")
        finally:
            if temp_clone_dir:
                shutil.rmtree(temp_clone_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
