"""Tests for the Chinese overlay git sync helper."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

from scripts.zh import sync


def completed(stdout: str = "") -> subprocess.CompletedProcess[str]:
    """Return a completed command result."""
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout)


def test_list_remotes_parses_fetch_and_push_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parse git remote output into Remote records."""

    def fake_run(
        args: Sequence[str],
        *,
        capture_output: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        assert list(args) == ["git", "remote", "-v"]
        return completed(
            "origin\tgit@github.com:Ikki6666/docs.git (fetch)\n"
            "origin\tgit@github.com:Ikki6666/docs.git (push)\n"
            "upstream\thttps://github.com/langchain-ai/docs.git (fetch)\n"
            "upstream\thttps://github.com/langchain-ai/docs.git (push)\n"
        )

    monkeypatch.setattr(sync, "run", fake_run)

    remotes = sync.list_remotes()

    assert remotes["origin"].fetch_url == "git@github.com:Ikki6666/docs.git"
    assert remotes["upstream"].fetch_url == "https://github.com/langchain-ai/docs.git"


def test_setup_remotes_renames_official_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rename official origin to upstream before adding the personal fork."""
    calls: list[list[str]] = []
    remote_outputs = iter(
        [
            "origin\thttps://github.com/langchain-ai/docs.git (fetch)\n"
            "origin\thttps://github.com/langchain-ai/docs.git (push)\n",
            "upstream\thttps://github.com/langchain-ai/docs.git (fetch)\n"
            "upstream\thttps://github.com/langchain-ai/docs.git (push)\n",
        ]
    )

    def fake_run(
        args: Sequence[str],
        *,
        capture_output: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        if list(args) == ["git", "remote", "-v"] and capture_output:
            return completed(next(remote_outputs))
        return completed()

    monkeypatch.setattr(sync, "run", fake_run)

    sync.setup_remotes(
        origin_url="git@github.com:Ikki6666/docs.git",
        upstream_url="https://github.com/langchain-ai/docs.git",
        assume_yes=True,
    )

    assert ["git", "remote", "rename", "origin", "upstream"] in calls
    assert [
        "git",
        "remote",
        "add",
        "origin",
        "git@github.com:Ikki6666/docs.git",
    ] in calls


def test_rev_counts_returns_left_and_right_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read ahead and behind counts from git rev-list."""

    def fake_run(
        args: Sequence[str],
        *,
        capture_output: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        assert list(args) == [
            "git",
            "rev-list",
            "--left-right",
            "--count",
            "HEAD...upstream/main",
        ]
        return completed("3\t11\n")

    monkeypatch.setattr(sync, "run", fake_run)

    assert sync.rev_counts("HEAD", "upstream/main") == (3, 11)
