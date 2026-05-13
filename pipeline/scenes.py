"""Stage 3 — segment chapters in `<book_dir>/analysis.json` into `<book_dir>/scenes.json`."""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "ai") not in sys.path:
    sys.path.insert(0, str(_ROOT / "ai"))

from ai.scene_segmentation import SceneSegmentation


def run(
    input_dir: Path | str,
    output_dir: Path | str,
    *,
    model: Optional[str] = None,
    windowed: bool = True,
    chapter_workers: int = 3,
    window_size: int = 4000,
    window_overlap: int = 500,
    workers: int = 4,
    chapters: Optional[List[int]] = None,
) -> Path:
    """Segment chapters in `<input_dir>/analysis.json`, writing/merging `<output_dir>/scenes.json`.

    If `chapters` is None and the scenes file already exists, returns immediately (idempotent).
    If `chapters` is provided, only missing chapter numbers in that set are segmented and merged.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    analysis_file = input_dir / "analysis.json"
    if not analysis_file.exists():
        raise FileNotFoundError(f"analysis.json not found in {input_dir}")

    with analysis_file.open() as f:
        analysis_data = json.load(f)
    chapters_list = (
        analysis_data["chapters"]
        if isinstance(analysis_data, dict) and "chapters" in analysis_data
        else analysis_data
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    scenes_file = output_dir / "scenes.json"

    existing_scenes: list[dict] = []
    if scenes_file.exists():
        try:
            existing_scenes = json.loads(scenes_file.read_text())
        except Exception:
            existing_scenes = []

    if chapters:
        requested_set = set(chapters)
        chapters_list = [
            ch for ch in chapters_list if ch.get("chapter_number", 0) in requested_set
        ]
        if not chapters_list:
            print(f"⚠️  No matching chapters in analysis for requested: {sorted(requested_set)}")
            return scenes_file
        existing_chapter_nums = {
            s.get("chapter_number", 0) for s in existing_scenes if isinstance(s, dict)
        }
        if requested_set.issubset(existing_chapter_nums):
            print(f"✅ Scenes already exist for chapters {sorted(requested_set)}")
            return scenes_file
        all_scenes = [
            s
            for s in existing_scenes
            if isinstance(s, dict) and s.get("chapter_number", 0) not in requested_set
        ]
    else:
        if scenes_file.exists():
            print(f"✅ scenes.json already exists at {scenes_file}; skipping (idempotent)")
            return scenes_file
        all_scenes = []

    seg = SceneSegmentation(model=model)

    def _segment_one(chapter: dict) -> list[dict]:
        content = chapter.get("raw_content", "")
        if not content or len(content) < 100:
            content = (chapter.get("scene_description", "") or "") + " " + (
                chapter.get("mood_description", "") or ""
            )
        if windowed:
            scenes = seg.segment_chapter_windowed(
                content,
                chapter["chapter_title"],
                window_size=max(1000, window_size),
                overlap=max(0, window_overlap),
                workers=max(1, workers),
            )
        else:
            scenes = seg.segment_chapter(content, chapter["chapter_title"])
        for scene in scenes:
            scene.chapter_number = chapter.get("chapter_number", 0)
            scene.chapter_title = chapter.get("chapter_title", "")
        return [s.__dict__ for s in scenes]

    if len(chapters_list) > 1 and chapter_workers > 1:
        print(
            f"🚀 Segmenting {len(chapters_list)} chapters in parallel "
            f"({min(chapter_workers, len(chapters_list))} workers)"
        )
        with ThreadPoolExecutor(max_workers=min(chapter_workers, len(chapters_list))) as ex:
            futures = [ex.submit(_segment_one, ch) for ch in chapters_list]
            for fut in as_completed(futures):
                try:
                    all_scenes.extend(fut.result())
                except Exception as e:
                    print(f"❌ Error segmenting chapter: {e}")
    else:
        for ch in chapters_list:
            try:
                all_scenes.extend(_segment_one(ch))
            except Exception as e:
                print(f"❌ Error segmenting chapter: {e}")

    scenes_file.write_text(json.dumps(all_scenes, indent=2))
    print(f"✅ Wrote {len(all_scenes)} scenes → {scenes_file}")
    return scenes_file
