"""Stage 2 — character image prompts + Gemini character images, driven by analysis.json."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "ai") not in sys.path:
    sys.path.insert(0, str(_ROOT / "ai"))

from ai.character_image_prompter import CharacterImagePrompt, CharacterImagePrompter
from ai.expression_prompter import ExpressionPrompter
from ai.gemini_image_generator import GENAI_AVAILABLE, GeminiImageGenerator


def run(
    analysis_path: Path | str,
    output_base: Path | str,
    *,
    model: Optional[str] = None,
    region: Optional[str] = None,
    profile: Optional[str] = None,
    style: Optional[str] = None,
    gemini_key: Optional[str] = None,
    gemini_model: Optional[str] = None,
    aspect_ratio: str = "1:1",
    skip_images: bool = False,
    skip_expressions: bool = True,
    delay: float = 1.0,
) -> Path:
    """Generate `<output_base>/<book>/{character_prompts.json,images/*.png}` from analysis.json.

    Returns the book directory.
    """
    analysis_path = Path(analysis_path)
    output_base = Path(output_base)

    if not analysis_path.exists():
        raise FileNotFoundError(f"Analysis file not found: {analysis_path}")

    region = region or os.getenv("AWS_REGION", "eu-central-1")
    profile = profile or os.getenv("AWS_PROFILE")
    model = model or os.getenv("BEDROCK_MODEL")
    gemini_key = gemini_key or os.getenv("GEMINI_API_KEY")
    gemini_model = gemini_model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-image")

    base_name = analysis_path.stem.replace("_analysis", "")
    book_dir = output_base / base_name
    book_dir.mkdir(parents=True, exist_ok=True)

    # Mirror the analysis file into the book dir under the canonical name
    canonical_analysis = book_dir / "analysis.json"
    if canonical_analysis.resolve() != analysis_path.resolve():
        shutil.copy2(analysis_path, canonical_analysis)

    prompts_file = book_dir / "character_prompts.json"
    images_dir = book_dir / "images"

    # --- prompts ---
    if prompts_file.exists():
        with prompts_file.open() as f:
            prompts_data = json.load(f)
        prompts = [CharacterImagePrompt.from_dict(p) for p in prompts_data]
        print(f"📝 Loaded {len(prompts)} existing character prompts")
    else:
        print("📝 Generating character prompts from analysis…")
        prompter = CharacterImagePrompter(region=region, model=model, profile=profile)
        prompts = prompter.generate_from_analysis_file(str(canonical_analysis))
        prompter.export_prompts(prompts, str(prompts_file), format="json")
        print(f"✅ Wrote {len(prompts)} character prompts: {prompts_file}")

    # --- optional expression prompts ---
    expressions_dir = book_dir / "prompts"
    generate_expressions_env = os.getenv("GENERATE_EXPRESSIONS", "false").lower() == "true"
    if (not skip_expressions) and generate_expressions_env:
        try:
            ExpressionPrompter().generate_from_character_prompts_file(
                str(prompts_file), str(expressions_dir)
            )
            print(f"✅ Wrote expression prompts: {expressions_dir}")
        except Exception as e:
            print(f"⚠️  Expression-prompt generation failed: {e}")

    # --- images ---
    if skip_images:
        return book_dir
    if not GENAI_AVAILABLE:
        raise RuntimeError("google-genai not installed; `pip install google-genai`")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY required for image generation")

    generator = GeminiImageGenerator(api_key=gemini_key, model=gemini_model)
    results = generator.generate_from_prompts_file(
        str(prompts_file),
        str(images_dir),
        aspect_ratio=aspect_ratio,
        delay_seconds=delay,
        style_suffix=style,  # only the explicit --style is forwarded; auto-detected style stays out of filenames
    )
    generator.export_generation_report(results, str(images_dir / "generation_report.json"))
    successes = sum(1 for r in results if r.success)
    print(f"✅ Generated {successes}/{len(results)} character images → {images_dir}")
    return book_dir
