"""In-process pipeline stages — replaces the per-stage `subprocess.run` chain in `book_to_vn.py`.

Each submodule exposes a `run(...)` callable that wraps the existing `ai/` classes.
The standalone CLI scripts (`analyze_chapters.py`, `generate_character_images.py`,
`ai/scene_segmentation.py`, `ai/consistent_scene_generator.py`) are still usable for
debugging; they now delegate to these functions.
"""

from . import analyze, characters, illustrate, scenes, worldsmith

__all__ = ["analyze", "characters", "illustrate", "scenes", "worldsmith"]
