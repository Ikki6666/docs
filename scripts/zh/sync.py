"""Sync a personal Chinese-overlay docs fork with upstream LangChain docs."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from scripts.zh.overlay import build_overlay, scan_status

DEFAULT_UPSTREAM_NAME = "upstream"
DEFAULT_UPSTREAM_URL = "https://github.com/langchain-ai/docs.git"
DEFAULT_ORIGIN_NAME = "origin"


@dataclass(frozen=True)
class Remote:
    """A git remote with fetch and push URLs."""

    name: str
    fetch_url: str
    push_url: str


def run(
    args: Sequence[str],
    *,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a command, optionally capturing stdout."""
    print(f"+ {' '.join(args)}")
    return subprocess.run(
        args,
        capture_output=capture_output,
        check=check,
        text=True,
    )


def yes_no(question: str, *, assume_yes: bool) -> bool:
    """Ask for confirmation unless --yes was provided."""
    if assume_yes:
        print(f"{question} yes")
        return True
    answer = input(f"{question} [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def list_remotes() -> dict[str, Remote]:
    """Return configured git remotes keyed by name."""
    result = run(["git", "remote", "-v"], capture_output=True)
    records: dict[str, dict[str, str]] = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        name, url, kind = parts[:3]
        kind = kind.strip("()")
        records.setdefault(name, {})[kind] = url
    return {
        name: Remote(name, urls.get("fetch", ""), urls.get("push", ""))
        for name, urls in records.items()
    }


def setup_remotes(
    *,
    origin_url: str,
    upstream_url: str,
    assume_yes: bool,
) -> int:
    """Configure origin as the personal fork and upstream as official docs."""
    remotes = list_remotes()
    origin = remotes.get(DEFAULT_ORIGIN_NAME)
    upstream = remotes.get(DEFAULT_UPSTREAM_NAME)

    if (
        origin
        and origin.fetch_url == upstream_url
        and upstream is None
        and yes_no("Rename official origin to upstream?", assume_yes=assume_yes)
    ):
        run(["git", "remote", "rename", DEFAULT_ORIGIN_NAME, DEFAULT_UPSTREAM_NAME])
        remotes = list_remotes()
        origin = remotes.get(DEFAULT_ORIGIN_NAME)
        upstream = remotes.get(DEFAULT_UPSTREAM_NAME)

    if upstream is None:
        run(["git", "remote", "add", DEFAULT_UPSTREAM_NAME, upstream_url])
    elif upstream.fetch_url != upstream_url and yes_no(
        f"Set upstream URL to {upstream_url}?",
        assume_yes=assume_yes,
    ):
        run(["git", "remote", "set-url", DEFAULT_UPSTREAM_NAME, upstream_url])

    if origin is None:
        run(["git", "remote", "add", DEFAULT_ORIGIN_NAME, origin_url])
    elif origin.fetch_url != origin_url and yes_no(
        f"Set origin URL to {origin_url}?",
        assume_yes=assume_yes,
    ):
        run(["git", "remote", "set-url", DEFAULT_ORIGIN_NAME, origin_url])

    run(["git", "remote", "-v"])
    return 0


def ensure_clean_worktree() -> None:
    """Abort if tracked or untracked files are present."""
    result = run(["git", "status", "--porcelain"], capture_output=True)
    if result.stdout.strip():
        print("Worktree is not clean. Commit or stash changes before syncing.")
        print(result.stdout, end="")
        raise SystemExit(1)


def current_branch() -> str:
    """Return the current branch name."""
    result = run(["git", "branch", "--show-current"], capture_output=True)
    branch = result.stdout.strip()
    if not branch:
        msg = "Detached HEAD is not supported by this helper."
        raise SystemExit(msg)
    return branch


def rev_counts(left: str, right: str) -> tuple[int, int]:
    """Return commits unique to left and right."""
    result = run(
        ["git", "rev-list", "--left-right", "--count", f"{left}...{right}"],
        capture_output=True,
    )
    left_count, right_count = result.stdout.split()
    return int(left_count), int(right_count)


def print_translation_summary() -> None:
    """Print a compact Chinese overlay status summary."""
    status = scan_status()
    print("Chinese overlay status:")
    for label in ("needs_update", "untranslated", "removed_upstream", "translated"):
        items = getattr(status, label)
        print(f"- {label}: {len(items)}")
        for item in items[:10]:
            print(f"  - {item}")
        if len(items) > 10:
            print(f"  ... {len(items) - 10} more")


def sync(
    *,
    upstream_ref: str,
    push: bool,
    assume_yes: bool,
) -> int:
    """Fetch upstream, merge official updates, build overlay, and optionally push."""
    ensure_clean_worktree()
    branch = current_branch()

    run(["git", "fetch", DEFAULT_UPSTREAM_NAME])
    ahead, behind = rev_counts("HEAD", upstream_ref)
    print(f"Compared with {upstream_ref}: ahead {ahead}, behind {behind}.")
    if behind and yes_no(f"Merge {upstream_ref} into {branch}?", assume_yes=assume_yes):
        run(["git", "merge", "--no-edit", upstream_ref])

    build_overlay()
    print_translation_summary()

    if push and yes_no(f"Push {branch} to origin?", assume_yes=assume_yes):
        run(["git", "push", "-u", DEFAULT_ORIGIN_NAME, branch])
    return 0


def status() -> int:
    """Show git remotes, branch state, and Chinese overlay summary."""
    run(["git", "remote", "-v"])
    run(["git", "status", "--short", "--branch"])
    print_translation_summary()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser("setup-remotes")
    setup_parser.add_argument("--origin-url", required=True)
    setup_parser.add_argument("--upstream-url", default=DEFAULT_UPSTREAM_URL)
    setup_parser.add_argument("-y", "--yes", action="store_true")

    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("--upstream-ref", default="upstream/main")
    sync_parser.add_argument("--push", action="store_true")
    sync_parser.add_argument("-y", "--yes", action="store_true")

    subparsers.add_parser("status")

    args = parser.parse_args(argv)
    if args.command == "setup-remotes":
        return setup_remotes(
            origin_url=args.origin_url,
            upstream_url=args.upstream_url,
            assume_yes=args.yes,
        )
    if args.command == "sync":
        return sync(
            upstream_ref=args.upstream_ref,
            push=args.push,
            assume_yes=args.yes,
        )
    if args.command == "status":
        return status()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
