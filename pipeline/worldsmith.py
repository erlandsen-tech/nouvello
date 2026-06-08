"""Worldsmith narrative stage (WORLDSMITH_INTEGRATION.md, C2).

Replaces the EPUB chapter-analysis → scenes "narrative brain" with the Worldsmith
engine. `run(book)` derives a prompt from the book's input flow, drives the engine
in autonomous mode, reads back the canon graph, and **maps it to the same
intermediate shapes the image stages already expect** — `character_prompts.json`
(consumed by `pipeline.characters`) and `scenes.json` (consumed by
`pipeline.illustrate`). The image stages then run unchanged.

The engine produces only *text*; all rendering stays consumer-side (D10).
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, List, Optional

from .worldsmith_client import GraphSnapshot, WorldsmithClient

_ROOT = Path(__file__).resolve().parent.parent

# Ordered bedtime story arc; used to sequence beats when `follows` edges are
# absent or incomplete, and to sort disconnected beats.
_PHASES = ["opening", "adventure", "wobble", "comfort", "sleep"]

DEFAULT_ART_STYLE = "soft watercolour children's picture-book illustration"


def run(
    book: dict,
    *,
    output_base: Optional[Path | str] = None,
    client: Optional[WorldsmithClient] = None,
) -> dict:
    """Build the canon-derived intermediate for one `books` row.

    Writes `<book_dir>/character_prompts.json` and `<book_dir>/scenes.json` (plus a
    minimal `analysis.json` so the existing stages find an art style/title), and
    returns a dict of paths + the mapped lists for the worker to render and upload.
    """
    book_id = str(book["id"])
    output_base = Path(output_base or os.getenv("WORKER_OUTPUT_BASE") or (_ROOT / "output"))
    book_dir = output_base / book_id
    book_dir.mkdir(parents=True, exist_ok=True)

    pack_id = os.getenv("WORLDSMITH_PACK_ID", "bedtime")
    pack_version = os.getenv("WORLDSMITH_PACK_VERSION", "0.1.0")
    art_style = book.get("art_style") or os.getenv("DEFAULT_ART_STYLE") or DEFAULT_ART_STYLE
    title = book.get("title") or "Eventyret"

    owns_client = client is None
    client = client or WorldsmithClient.from_env()
    try:
        prompt = _derive_prompt(book)
        world_id = client.create_world(pack_id, pack_version)
        client.run_agent(world_id, prompt, pack_id, mode="autonomous")
        graph = client.query_graph(world_id)
    finally:
        if owns_client:
            client.close()

    characters = _map_characters(graph, art_style)
    scenes = _map_scenes(graph, art_style)

    # Minimal analysis.json: the character/illustrate stages read `art_style` and a
    # title from here; chapters stay empty because the brain is now Worldsmith.
    analysis_path = output_base / f"{book_id}_analysis.json"
    analysis_path.write_text(
        json.dumps(
            {"book_title": title, "art_style": art_style, "world_id": world_id, "chapters": []},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (book_dir / "character_prompts.json").write_text(
        json.dumps(characters, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (book_dir / "scenes.json").write_text(
        json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "book_id": book_id,
        "world_id": world_id,
        "output_base": str(output_base),
        "book_dir": str(book_dir),
        "analysis_path": str(analysis_path),
        "scenes_path": str(book_dir / "scenes.json"),
        "images_dir": str(book_dir / "images"),
        "scenes_out_dir": str(book_dir / "consistent_scenes"),
        "art_style": art_style,
        "title": title,
        "characters": characters,
        "scenes": scenes,
    }


# ---------------------------------------------------------------------------
# prompt + persona derivation (consumer-side; the engine ingests text only)
# ---------------------------------------------------------------------------

def _derive_prompt(book: dict) -> str:
    kind = book.get("input_kind") or "write"
    payload = book.get("input_payload") or {}
    persona = _persona_text(book, payload, kind)

    if kind == "guided":
        bits = []
        for key, label in (
            ("hero", "Helt"),
            ("setting", "Sted"),
            ("problem", "Floke"),
            ("lesson", "Lærdom"),
        ):
            value = payload.get(key)
            if value:
                bits.append(f"{label}: {value}")
        framing = "Lag en rolig leggetids-billedbok med disse ingrediensene:\n" + "\n".join(bits)
    elif kind in ("photo", "drawing"):
        subject = payload.get("text") or payload.get("notes") or ""
        framing = (
            "Lag en rolig leggetids-billedbok der helten er barnets egen figur.\n"
            + subject
        ).strip()
    else:  # "write" and any unknown kind fall back to free text
        core = payload.get("text") or payload.get("prompt") or payload.get("story") or ""
        framing = f"Lag en rolig leggetids-billedbok basert på denne idéen:\n{core}".strip()

    parts = [framing]
    if persona:
        parts.append(f"\nDetaljer om hovedfiguren som skal beholdes:\n{persona}")
    parts.append(
        "\nBygg en kort leggetids-bue av story beats fra opening til sleep, "
        "med en liten rollebesetning og et koselig sted."
    )
    return "\n".join(p for p in parts if p).strip()


def _persona_text(book: dict, payload: dict, kind: str) -> str:
    """Text persona attributes for the hero. Photo/drawing → text is a consumer step."""
    explicit = payload.get("persona") or payload.get("child_description")
    if explicit:
        return explicit if isinstance(explicit, str) else json.dumps(explicit, ensure_ascii=False)
    if kind in ("photo", "drawing"):
        # TODO(C3): run a vision/transcription model over book["child_photo_url"] /
        # the uploaded drawing to extract text persona attributes. The engine
        # ingests text only — until then, fall back to whatever text the parent gave.
        name = payload.get("child_name") or payload.get("name")
        if name:
            return f"Helten er inspirert av {name}."
    return ""


# ---------------------------------------------------------------------------
# canon → intermediate mapping (bedtime pack)
# ---------------------------------------------------------------------------

def _map_characters(graph: GraphSnapshot, art_style: str) -> List[dict]:
    """`character` nodes → CharacterImagePrompt dicts (pipeline.characters input)."""
    style_tags = [t.strip() for t in art_style.split(",") if t.strip()] if art_style else []
    out: List[dict] = []
    for node in graph.get("nodes", []):
        if node.get("type") != "character":
            continue
        name = node.get("label") or node.get("id") or "Helt"
        attrs = node.get("attributes") or {}
        appearance = attrs.get("appearance") or {}
        description = appearance.get("description") or node.get("summary") or f"a character named {name}"
        features = appearance.get("features") or {}
        feature_text = "; ".join(f"{k}: {v}" for k, v in features.items())

        prompt_bits = [description]
        if feature_text:
            prompt_bits.append(feature_text)
        image_prompt = ". ".join(b for b in prompt_bits if b)
        if art_style:
            image_prompt = (
                f"{image_prompt}. Full-body character portrait, plain neutral "
                f"background, {art_style}."
            )
        out.append(
            {
                "character_name": name,
                "image_prompt": image_prompt,
                "style_tags": style_tags,
                "book_context": "",
                "chapter_references": [],
            }
        )
    return out


def _map_scenes(graph: GraphSnapshot, art_style: str) -> List[dict]:
    """`story_beat` nodes (ordered by `follows`) → SceneSegment dicts."""
    nodes = {n["id"]: n for n in graph.get("nodes", []) if "id" in n}
    edges = graph.get("edges", [])
    beats = [n for n in nodes.values() if n.get("type") == "story_beat"]
    ordered = _order_beats(beats, edges)

    appears_in: dict[str, list[str]] = defaultdict(list)  # beat_id -> [character_id]
    set_in: dict[str, str] = {}                           # beat_id -> place_id
    holds: dict[str, list[str]] = defaultdict(list)       # character_id -> [keepsake_id]
    for edge in edges:
        relation, source, target = edge.get("relation"), edge.get("source"), edge.get("target")
        if relation == "appears_in":   # character -> story_beat
            appears_in[target].append(source)
        elif relation == "set_in":     # story_beat -> place
            set_in[source] = target
        elif relation == "holds":      # character -> keepsake
            holds[source].append(target)

    def label_of(node_id: str) -> str:
        node = nodes.get(node_id) or {}
        return node.get("label") or node_id

    scenes: List[dict] = []
    for idx, beat in enumerate(ordered, start=1):
        battrs = beat.get("attributes") or {}
        beat_id = beat["id"]
        present = appears_in.get(beat_id, [])
        characters_present = [label_of(cid) for cid in present]

        place = nodes.get(set_in.get(beat_id, ""), {})
        pattrs = place.get("attributes") or {}
        setting = place.get("label") or pattrs.get("setting") or ""
        if pattrs.get("setting") and pattrs["setting"] not in setting:
            setting = f"{setting} — {pattrs['setting']}".strip(" —")
        mood = pattrs.get("mood") or battrs.get("phase") or ""

        props = [label_of(kid) for cid in present for kid in holds.get(cid, [])]

        text = beat.get("summary") or beat.get("label") or ""
        title = beat.get("label") or f"Side {idx}"

        prompt_bits = [text]
        if setting:
            prompt_bits.append(f"Setting: {setting}.")
        if props:
            prompt_bits.append(f"Featuring: {', '.join(props)}.")
        if mood:
            prompt_bits.append(f"Mood: {mood}.")
        image_prompt = " ".join(b for b in prompt_bits if b)

        scenes.append(
            {
                "scene_number": idx,
                "title": title,
                "content": text,
                "characters_present": characters_present,
                "setting": setting,
                "mood": mood,
                "image_prompt": image_prompt,
                "image_type": "scene" if characters_present else "environment",
                "image_file": "",
                "chapter_number": 0,
                "chapter_title": battrs.get("phase", ""),
            }
        )
    return scenes


def _phase_rank(node: dict) -> int:
    phase = ((node.get("attributes") or {}).get("phase") or "").lower()
    return _PHASES.index(phase) if phase in _PHASES else len(_PHASES)


def _order_beats(beats: List[dict], edges: List[dict]) -> List[dict]:
    """Order beats by the `follows` edge chain; fall back to phase order.

    `follows` reads "source follows target", so `target` precedes `source`.
    """
    by_id = {b["id"]: b for b in beats}
    ids = set(by_id)
    next_of: dict[str, str] = {}   # predecessor -> successor
    prev_of: dict[str, str] = {}   # successor -> predecessor
    for edge in edges:
        if edge.get("relation") != "follows":
            continue
        source, target = edge.get("source"), edge.get("target")
        if source in ids and target in ids:
            prev_of[source] = target
            next_of[target] = source

    if not next_of and not prev_of:
        return sorted(beats, key=_phase_rank)

    heads = sorted((bid for bid in ids if bid not in prev_of), key=lambda b: _phase_rank(by_id[b]))
    ordered: List[dict] = []
    seen: set[str] = set()
    for head in heads:
        cur: Optional[str] = head
        while cur is not None and cur not in seen:
            seen.add(cur)
            ordered.append(by_id[cur])
            cur = next_of.get(cur)
    # Any beats left out of the chain (cycle / disconnected) — append by phase.
    ordered.extend(sorted((by_id[b] for b in ids if b not in seen), key=_phase_rank))
    return ordered
