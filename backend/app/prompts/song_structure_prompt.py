"""Prompt template and schema for song structure analysis."""

from __future__ import annotations


SONG_STRUCTURE_SCHEMA = {
    "type": "object",
    "properties": {
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "enum": ["intro", "verse", "chorus", "bridge", "outro", "pre-chorus", "post-chorus"],
                    },
                    "index": {"type": "integer"},
                    "summary": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "confidence": {"type": "number"},
                },
                "required": [
                    "label",
                    "index",
                    "summary",
                    "start_line",
                    "end_line",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        },
        "energy_progression": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section_index": {"type": "integer"},
                    "label": {"type": "string"},
                    "energy_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "peak"],
                    },
                    "reason": {"type": "string"},
                },
                "required": ["section_index", "label", "energy_level", "reason"],
                "additionalProperties": False,
            },
        },
        "difficult_sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section_index": {"type": "integer"},
                    "label": {"type": "string"},
                    "difficulty_level": {
                        "type": "string",
                        "enum": ["moderate", "high", "very_high"],
                    },
                    "reason": {"type": "string"},
                },
                "required": ["section_index", "label", "difficulty_level", "reason"],
                "additionalProperties": False,
            },
        },
        "overall_summary": {"type": "string"},
    },
    "required": [
        "sections",
        "energy_progression",
        "difficult_sections",
        "overall_summary",
    ],
    "additionalProperties": False,
}


def build_song_structure_instructions() -> str:
    """Return the system/developer instructions for structure analysis."""
    return (
        "You analyze songs for karaoke performance preparation. "
        "Return only structured JSON matching the provided schema. "
        "Infer likely song sections from lyrics repetition, lyrical transitions, tempo, and key context. "
        "Use the most probable labels among intro, verse, chorus, bridge, outro, pre-chorus, and post-chorus. "
        "Confidence must be between 0 and 1. "
        "If a section is uncertain, still choose the best label and reflect uncertainty in confidence and summary wording. "
        "Difficult sections should focus on parts that are likely demanding for a singer, such as repeated climactic hooks, "
        "dense phrasing, sustained notes, fast articulation, or dynamic jumps. "
        "Energy progression should describe how the song intensity changes across sections."
    )


def build_song_structure_input(
    *,
    lyrics: str,
    tempo: float,
    key: str,
    song_title: str | None = None,
    artist_name: str | None = None,
) -> str:
    """Build the user payload for structure analysis."""
    title_line = song_title or "Unknown"
    artist_line = artist_name or "Unknown"
    return (
        "Analyze the following song and identify its structure.\n\n"
        f"Song title: {title_line}\n"
        f"Artist: {artist_line}\n"
        f"Tempo (BPM): {tempo}\n"
        f"Key: {key}\n\n"
        "Lyrics:\n"
        f"{lyrics.strip()}\n\n"
        "Return JSON with:\n"
        "- sections in sequence order\n"
        "- energy progression by section\n"
        "- difficult sections for karaoke performance\n"
        "- one overall summary"
    )
