"""Tests for the Chinese documentation overlay helpers."""

import json
from pathlib import Path
from types import SimpleNamespace

from pipeline.commands.build import build_command
from scripts.zh.overlay import build_overlay, scan_status, stamp_translations


def test_build_overlay_replaces_translated_files_and_keeps_fallbacks(
    tmp_path: Path,
) -> None:
    """Overlay translated files while keeping untranslated source files."""
    src_dir = tmp_path / "src"
    translations_src_dir = tmp_path / "translations" / "zh" / "src"
    output_src_dir = tmp_path / ".generated" / "zh" / "src"

    (src_dir / "oss").mkdir(parents=True)
    (translations_src_dir / "oss").mkdir(parents=True)

    (src_dir / "index.mdx").write_text("# Home\n", encoding="utf-8")
    (src_dir / "oss" / "guide.mdx").write_text("# Guide\n", encoding="utf-8")
    (translations_src_dir / "index.mdx").write_text("# 首页\n", encoding="utf-8")

    build_overlay(src_dir, translations_src_dir, output_src_dir)

    assert (output_src_dir / "index.mdx").read_text(encoding="utf-8") == "# 首页\n"
    assert (output_src_dir / "oss" / "guide.mdx").read_text(
        encoding="utf-8"
    ) == "# Guide\n"


def test_scan_status_reports_untranslated_needs_update_and_removed_upstream(
    tmp_path: Path,
) -> None:
    """Report the three translation maintenance states."""
    src_dir = tmp_path / "src"
    translations_src_dir = tmp_path / "translations" / "zh" / "src"
    manifest_path = tmp_path / "translations" / "zh" / "manifest.json"

    (src_dir / "oss").mkdir(parents=True)
    (translations_src_dir / "oss").mkdir(parents=True)

    (src_dir / "index.mdx").write_text("# Home v2\n", encoding="utf-8")
    (src_dir / "oss" / "guide.mdx").write_text("# Guide\n", encoding="utf-8")
    (src_dir / "code-samples").mkdir()
    (src_dir / "code-samples" / "package.json").write_text("{}", encoding="utf-8")
    (translations_src_dir / "index.mdx").write_text("# 首页\n", encoding="utf-8")
    (translations_src_dir / "oss" / "removed.mdx").write_text(
        "# 已删除\n", encoding="utf-8"
    )
    manifest_path.write_text(
        json.dumps(
            {
                "src/index.mdx": {"source_sha256": "old"},
                "src/oss/removed.mdx": {"source_sha256": "old"},
            }
        ),
        encoding="utf-8",
    )

    status = scan_status(src_dir, translations_src_dir, manifest_path)

    assert status.needs_update == ["src/index.mdx"]
    assert status.untranslated == ["src/oss/guide.mdx"]
    assert status.removed_upstream == ["src/oss/removed.mdx"]


def test_stamp_translations_records_current_source_hash(tmp_path: Path) -> None:
    """Stamp translated files with the current source digest."""
    src_dir = tmp_path / "src"
    translations_src_dir = tmp_path / "translations" / "zh" / "src"
    manifest_path = tmp_path / "translations" / "zh" / "manifest.json"

    src_dir.mkdir()
    translations_src_dir.mkdir(parents=True)
    (src_dir / "index.mdx").write_text("# Home\n", encoding="utf-8")
    (translations_src_dir / "index.mdx").write_text("# 首页\n", encoding="utf-8")

    stamp_translations(src_dir, translations_src_dir, manifest_path)
    status = scan_status(src_dir, translations_src_dir, manifest_path)

    assert status.needs_update == []
    assert status.untranslated == []
    assert status.translated == ["src/index.mdx"]


def test_build_command_accepts_custom_source_and_build_dirs(tmp_path: Path) -> None:
    """Build from a generated source directory into a selected build directory."""
    custom_src = tmp_path / "custom-src"
    custom_build = tmp_path / "custom-build"
    custom_src.mkdir()
    (custom_src / "index.mdx").write_text("# 首页\n", encoding="utf-8")

    result = build_command(
        SimpleNamespace(src_dir=str(custom_src), build_dir=str(custom_build))
    )

    assert result == 0
    assert (custom_build / "index.mdx").exists()


def test_build_overlay_links_node_modules_for_builder(tmp_path: Path) -> None:
    """Expose project node_modules next to the overlay so the builder finds it."""
    src_dir = tmp_path / "src"
    translations_src_dir = tmp_path / "translations" / "zh" / "src"
    output_src_dir = tmp_path / ".generated" / "zh" / "src"

    src_dir.mkdir()
    (src_dir / "index.mdx").write_text("# Home\n", encoding="utf-8")
    translations_src_dir.mkdir(parents=True)
    (translations_src_dir / "index.mdx").write_text("# 首页\n", encoding="utf-8")

    sandbox_dist = tmp_path / "node_modules" / "@langchain" / "docs-sandbox" / "dist"
    sandbox_dist.mkdir(parents=True)
    (sandbox_dist / "PatternEmbed.jsx").write_text("// built", encoding="utf-8")

    build_overlay(src_dir, translations_src_dir, output_src_dir)

    link = output_src_dir.parent / "node_modules"
    assert link.is_symlink()
    assert (
        link / "@langchain" / "docs-sandbox" / "dist" / "PatternEmbed.jsx"
    ).read_text(encoding="utf-8") == "// built"


def test_build_overlay_skips_link_when_node_modules_missing(tmp_path: Path) -> None:
    """Skip the node_modules link without error when npm install has not run."""
    src_dir = tmp_path / "src"
    output_src_dir = tmp_path / ".generated" / "zh" / "src"

    src_dir.mkdir()
    (src_dir / "index.mdx").write_text("# Home\n", encoding="utf-8")

    build_overlay(src_dir, src_dir / "_unused_translations", output_src_dir)

    assert not (output_src_dir.parent / "node_modules").exists()
