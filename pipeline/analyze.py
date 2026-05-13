"""Stage 1 — analyze an EPUB's chapters into `<output_dir>/<book_stem>_analysis.json`."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "ai") not in sys.path:
    sys.path.insert(0, str(_ROOT / "ai"))

from ai.chapter_analyzer import ChapterAnalyzer
from ai.character_image_prompter import CharacterImagePrompter
from ai.epub_parser import EPUBParser


def run(
    epub_path: Path | str,
    output_dir: Path | str,
    chapter_indices: Optional[List[int]] = None,
    *,
    model: Optional[str] = None,
    region: Optional[str] = None,
    profile: Optional[str] = None,
    style: Optional[str] = None,
) -> Path:
    """Analyze selected chapters of an EPUB.

    `chapter_indices` is 0-based (matches the `-c` flag on `analyze_chapters.py`).
    If `style` is None, an art style is inferred from the analyzed chapters.
    Returns the path of the written `<book_stem>_analysis.json`.
    """
    epub_path = Path(epub_path)
    output_dir = Path(output_dir)

    if not epub_path.exists():
        raise FileNotFoundError(f"EPUB file not found: {epub_path}")

    region = region or os.getenv("AWS_REGION", "eu-central-1")
    profile = profile or os.getenv("AWS_PROFILE")
    model = model or os.getenv("BEDROCK_MODEL")

    parser_obj = EPUBParser(str(epub_path))
    chapters = parser_obj.parse()
    if not chapters:
        raise RuntimeError(f"No chapters found in EPUB: {epub_path}")

    book_title = parser_obj.get_book_title()
    book_author = parser_obj.get_book_author()

    if chapter_indices is not None:
        chapter_indices = sorted({i for i in chapter_indices if 0 <= i < len(chapters)})
        if not chapter_indices:
            raise ValueError(f"No valid chapter indices for EPUB with {len(chapters)} chapters")

    print(f"📚 Analyzing {len(chapter_indices) if chapter_indices is not None else len(chapters)} chapters of {epub_path.name}")

    analyzer = ChapterAnalyzer(region=region, model=model, profile=profile)
    analyses = analyzer.analyze_chapters(chapters, chapter_indices)
    if not analyses:
        raise RuntimeError("Chapter analyzer returned no analyses")

    inferred_style: Optional[str] = None
    if not style:
        try:
            prompter = CharacterImagePrompter(region=region, model=model, profile=profile)
            book_context = prompter._extract_book_context(analyses)
            tags = book_context.get("art_style_tags", [])
            if tags:
                inferred_style = ", ".join(tags)
                print(f"🎨 Inferred art style: {inferred_style}")
        except Exception as e:
            print(f"⚠️  Could not infer art style: {e}")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{epub_path.stem}_analysis.json"
    data = {
        "book_title": book_title,
        "book_author": book_author,
        "art_style": style or inferred_style,
        "chapters": [a.to_dict() for a in analyses],
    }
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Wrote analysis: {out_path}")
    return out_path
