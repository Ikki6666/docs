"""Build and inspect the local Chinese documentation overlay."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DOC_EXTENSIONS = {".md", ".mdx"}
IGNORED_DOC_DIRS = {"code-samples", ".mintlify"}
DEFAULT_SRC_DIR = Path("src")
DEFAULT_TRANSLATIONS_SRC_DIR = Path("translations/zh/src")
DEFAULT_OUTPUT_SRC_DIR = Path(".generated/zh/src")
DEFAULT_MANIFEST_PATH = Path("translations/zh/manifest.json")


@dataclass(frozen=True)
class TranslationStatus:
    """Summary of the current Chinese translation coverage."""

    translated: list[str]
    needs_update: list[str]
    untranslated: list[str]
    removed_upstream: list[str]


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_overlay(
    src_dir: Path = DEFAULT_SRC_DIR,
    translations_src_dir: Path = DEFAULT_TRANSLATIONS_SRC_DIR,
    output_src_dir: Path = DEFAULT_OUTPUT_SRC_DIR,
) -> None:
    """Generate a source tree that overlays Chinese files on top of English."""
    if not src_dir.exists():
        msg = f"Source directory not found: {src_dir}"
        raise FileNotFoundError(msg)

    if output_src_dir.exists():
        shutil.rmtree(output_src_dir)
    output_src_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, output_src_dir)

    if not translations_src_dir.exists():
        return

    for translated_file in _iter_files(translations_src_dir):
        relative_path = translated_file.relative_to(translations_src_dir)
        output_file = output_src_dir / relative_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(translated_file, output_file)


def scan_status(
    src_dir: Path = DEFAULT_SRC_DIR,
    translations_src_dir: Path = DEFAULT_TRANSLATIONS_SRC_DIR,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> TranslationStatus:
    """Compare source docs, translated docs, and recorded source hashes."""
    manifest = _load_manifest(manifest_path)
    source_files = {_source_key(path, src_dir): path for path in _iter_docs(src_dir)}
    translated_files = {
        _source_key(path, translations_src_dir): path
        for path in _iter_docs(translations_src_dir)
    }

    translated: list[str] = []
    needs_update: list[str] = []
    untranslated: list[str] = []
    removed_upstream = {key for key in manifest if key not in source_files} | {
        key for key in translated_files if key not in source_files
    }

    for key, source_file in source_files.items():
        translated_file = translated_files.get(key)
        if translated_file is None:
            untranslated.append(key)
            continue

        current_hash = file_sha256(source_file)
        recorded_hash = manifest.get(key, {}).get("source_sha256")
        if recorded_hash == current_hash:
            translated.append(key)
        else:
            needs_update.append(key)

    return TranslationStatus(
        translated=sorted(translated),
        needs_update=sorted(needs_update),
        untranslated=sorted(untranslated),
        removed_upstream=sorted(removed_upstream),
    )


def stamp_translations(
    src_dir: Path = DEFAULT_SRC_DIR,
    translations_src_dir: Path = DEFAULT_TRANSLATIONS_SRC_DIR,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    paths: list[str] | None = None,
) -> None:
    """Record current source hashes for translated files."""
    manifest = _load_manifest(manifest_path)
    source_files = {_source_key(path, src_dir): path for path in _iter_docs(src_dir)}
    translated_keys = {
        _source_key(path, translations_src_dir)
        for path in _iter_docs(translations_src_dir)
    }
    keys_to_stamp = (
        sorted(translated_keys) if paths is None else [_normalize_key(p) for p in paths]
    )

    for key in keys_to_stamp:
        source_file = source_files.get(key)
        if source_file is None:
            continue
        manifest[key] = {"source_sha256": file_sha256(source_file)}

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def _iter_docs(root: Path) -> list[Path]:
    return [path for path in _iter_files(root) if _is_translatable_doc(path, root)]


def _is_translatable_doc(path: Path, root: Path) -> bool:
    relative_path = path.relative_to(root)
    if relative_path.parts[0] in IGNORED_DOC_DIRS:
        return False
    return path.suffix in DOC_EXTENSIONS or relative_path.as_posix() == "docs.json"


def _source_key(path: Path, root: Path) -> str:
    return f"src/{path.relative_to(root).as_posix()}"


def _normalize_key(path: str) -> str:
    normalized = path.removeprefix("./")
    if normalized.startswith("src/"):
        return normalized
    return f"src/{normalized}"


def _load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _print_status(status: TranslationStatus) -> None:
    for label, paths in (
        ("needs_update", status.needs_update),
        ("untranslated", status.untranslated),
        ("removed_upstream", status.removed_upstream),
        ("translated", status.translated),
    ):
        print(f"{label}:")
        for path in paths:
            print(f"- {path}")
        if not paths:
            print("- none")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--src-dir", type=Path, default=DEFAULT_SRC_DIR)
    build_parser.add_argument(
        "--translations-src-dir",
        type=Path,
        default=DEFAULT_TRANSLATIONS_SRC_DIR,
    )
    build_parser.add_argument(
        "--output-src-dir",
        type=Path,
        default=DEFAULT_OUTPUT_SRC_DIR,
    )

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--src-dir", type=Path, default=DEFAULT_SRC_DIR)
    status_parser.add_argument(
        "--translations-src-dir",
        type=Path,
        default=DEFAULT_TRANSLATIONS_SRC_DIR,
    )
    status_parser.add_argument(
        "--manifest-path",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
    )

    stamp_parser = subparsers.add_parser("stamp")
    stamp_parser.add_argument("paths", nargs="*")
    stamp_parser.add_argument("--src-dir", type=Path, default=DEFAULT_SRC_DIR)
    stamp_parser.add_argument(
        "--translations-src-dir",
        type=Path,
        default=DEFAULT_TRANSLATIONS_SRC_DIR,
    )
    stamp_parser.add_argument(
        "--manifest-path",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
    )

    args = parser.parse_args()
    if args.command == "build":
        build_overlay(args.src_dir, args.translations_src_dir, args.output_src_dir)
        return 0
    if args.command == "status":
        status = scan_status(
            args.src_dir,
            args.translations_src_dir,
            args.manifest_path,
        )
        _print_status(status)
        return 0
    if args.command == "stamp":
        stamp_translations(
            args.src_dir,
            args.translations_src_dir,
            args.manifest_path,
            args.paths or None,
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
