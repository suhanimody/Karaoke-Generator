"""Service for analyzing song structure with the OpenAI API."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from backend.app.prompts.song_structure_prompt import (
    SONG_STRUCTURE_SCHEMA,
    build_song_structure_input,
    build_song_structure_instructions,
)


class SongStructureAnalysisError(Exception):
    """Raised when song structure analysis fails."""


class SongStructureAnalysisService:
    """Analyze song structure, energy progression, and difficult sections."""

    def __init__(
        self,
        client: OpenAI | None = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        self._client = client
        self._model = model

    def analyze(
        self,
        *,
        lyrics: str,
        tempo: float,
        key: str,
        song_title: str | None = None,
        artist_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze song structure using the OpenAI Responses API.

        Returns:
            A structured JSON-compatible dictionary with section labels and metadata.

        Raises:
            SongStructureAnalysisError: The request or response is invalid.
        """
        if not lyrics or not lyrics.strip():
            raise SongStructureAnalysisError("Lyrics are required for song structure analysis.")

        if tempo <= 0:
            raise SongStructureAnalysisError("Tempo must be a positive number.")

        if not key or not key.strip():
            raise SongStructureAnalysisError("Key is required for song structure analysis.")

        try:
            response = self._get_client().responses.create(
                model=self._model,
                instructions=build_song_structure_instructions(),
                input=build_song_structure_input(
                    lyrics=lyrics,
                    tempo=tempo,
                    key=key,
                    song_title=song_title,
                    artist_name=artist_name,
                ),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "song_structure_analysis",
                        "strict": True,
                        "schema": SONG_STRUCTURE_SCHEMA,
                    }
                },
            )
        except Exception as exc:
            raise SongStructureAnalysisError(
                "OpenAI song structure analysis request failed."
            ) from exc

        raw_output = getattr(response, "output_text", None)
        if not raw_output:
            raise SongStructureAnalysisError("OpenAI returned an empty structure analysis response.")

        try:
            parsed_output = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise SongStructureAnalysisError(
                "OpenAI returned a non-JSON structure analysis response."
            ) from exc

        self._validate_required_top_level_fields(parsed_output)
        return parsed_output

    def _validate_required_top_level_fields(self, payload: dict[str, Any]) -> None:
        required_fields = {
            "sections",
            "energy_progression",
            "difficult_sections",
            "overall_summary",
        }
        missing_fields = required_fields.difference(payload.keys())
        if missing_fields:
            missing_list = ", ".join(sorted(missing_fields))
            raise SongStructureAnalysisError(
                f"OpenAI response is missing required fields: {missing_list}"
            )

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI()
        return self._client
