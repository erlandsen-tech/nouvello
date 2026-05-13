"""Stage 4 — generate per-scene illustrations with consistent character refs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "ai") not in sys.path:
    sys.path.insert(0, str(_ROOT / "ai"))

from ai.consistent_scene_generator import ConsistentSceneGenerator, SceneSegment


def run(
    scenes_file: Path | str,
    characters_dir: Path | str,
    output_dir: Path | str,
    *,
    delay: float = 2.0,
    art_style: Optional[str] = None,
    explicit_style: Optional[str] = None,
) -> Path:
    """Render consistent scene illustrations to `<output_dir>/scene_NN_*.png`.

    `art_style` flavors the prompt text (auto-picked up from sibling analysis.json when None).
    `explicit_style` is only set when the user passed `--style`; it affects character-image filename lookup.
    Returns `output_dir`.
    """
    scenes_file = Path(scenes_file)
    characters_dir = Path(characters_dir)
    output_dir = Path(output_dir)

    if not scenes_file.exists():
        raise FileNotFoundError(f"Scenes file not found: {scenes_file}")
    if not characters_dir.exists():
        raise FileNotFoundError(f"Character images directory not found: {characters_dir}")

    scenes_data = json.loads(scenes_file.read_text())
    scenes = [SceneSegment(**s) for s in scenes_data]
    output_dir.mkdir(parents=True, exist_ok=True)

    if not scenes:
        print("⚠️  No scenes to render")
        return output_dir

    all_exist = True
    for scene in scenes:
        safe_title = (
            scene.title.lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("'", "")
            .replace('"', "")
        )
        safe_title = "".join(c for c in safe_title if c.isalnum() or c == "_")
        expected = output_dir / f"scene_{scene.scene_number:02d}_{safe_title}.png"
        if not expected.exists():
            all_exist = False
            break
    if all_exist:
        print(f"✅ All {len(scenes)} scene images already exist → {output_dir}")
        return output_dir

    if art_style is None:
        analysis_file = scenes_file.parent / "analysis.json"
        if analysis_file.exists():
            try:
                analysis = json.loads(analysis_file.read_text())
                if isinstance(analysis, dict):
                    art_style = analysis.get("art_style")
                    if art_style:
                        print(f"🎨 Using art style from analysis.json: {art_style}")
            except Exception:
                pass

    generator = ConsistentSceneGenerator(art_style=art_style, explicit_style=explicit_style)
    generator.generate_consistent_scenes(scenes, characters_dir, output_dir, delay)
    return output_dir
