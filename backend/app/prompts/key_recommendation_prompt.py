"""Prompt template and schema for singer key-shift recommendations."""

from __future__ import annotations

import json
from typing import Any


KEY_RECOMMENDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "primary": {"type": "string"},
        "alternatives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "enum": ["safer", "closer_to_original"],
                    },
                    "shift": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["label", "shift", "reason"],
                "additionalProperties": False,
            },
            "minItems": 2,
            "maxItems": 2,
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
        "reasoning": {"type": "string"},
    },
    "required": ["primary", "alternatives", "confidence", "reasoning"],
    "additionalProperties": False,
}


def build_key_recommendation_instructions() -> str:
    """Return system instructions for key-shift recommendation."""
    return (
        "You recommend karaoke key shifts for a singer who struggles with high notes. "
        "Return only structured JSON matching the provided schema. "
        "Recommendations must make musical sense and generally prefer shifting downward rather than upward. "
        "Use the detected song key and song structure to infer where the singer is likely to strain, especially in choruses, bridges, and difficult sections. "
        "The primary recommendation should balance comfort and preserving song character. "
        "The safer alternative should be easier to sing than the primary recommendation. "
        "The closer_to_original alternative should preserve the original feel more closely than the primary recommendation. "
        "Use concise, explicit shift text such as 'Down 2 semitones to F major'. "
        "Confidence must be between 0 and 1. "
        "If the evidence is limited, lower confidence rather than overclaiming."
    )


def build_key_recommendation_input(
    *,
    detected_key: str,
    song_structure: dict[str, Any],
    singer_constraint: str = "Singer struggles with high notes.",
    song_title: str | None = None,
    artist_name: str | None = None,
) -> str:
    """Build the user payload for key recommendation."""
    title_line = song_title or "Unknown"
    artist_line = artist_name or "Unknown"
    serialized_structure = json.dumps(song_structure, indent=2)

    return (
        "Recommend a key shift for karaoke performance.\n\n"
        f"Song title: {title_line}\n"
        f"Artist: {artist_line}\n"
        f"Detected key: {detected_key}\n"
        f"Singer constraint: {singer_constraint}\n\n"
        "Known song structure analysis:\n"
        f"{serialized_structure}\n\n"
        "Return JSON with:\n"
        "- one primary recommendation\n"
        "- one safer alternative\n"
        "- one closer_to_original alternative\n"
        "- confidence score\n"
        "- concise musical reasoning"
    )
