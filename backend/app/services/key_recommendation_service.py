"""Service for recommending a singer-friendly key shift with the OpenAI API."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from backend.app.prompts.key_recommendation_prompt import (
    KEY_RECOMMENDATION_SCHEMA,
    build_key_recommendation_input,
    build_key_recommendation_instructions,
)


class KeyRecommendationError(Exception):
    """Raised when key recommendation fails."""


class KeyRecommendationService:
    """Recommend a key shift for singers who struggle with high notes."""

    def __init__(
        self,
        client: OpenAI | None = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        self._client = client
        self._model = model

    def recommend(
        self,
        *,
        detected_key: str,
        song_structure: dict[str, Any],
        singer_constraint: str = "Singer struggles with high notes.",
        song_title: str | None = None,
        artist_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Recommend an overall key shift with two alternatives.

        Returns:
            A JSON-compatible dictionary containing the primary recommendation,
            alternatives, confidence, and reasoning.
        """
        if not detected_key or not detected_key.strip():
            raise KeyRecommendationError("Detected key is required for recommendation.")

        if not isinstance(song_structure, dict) or not song_structure:
            raise KeyRecommendationError("Song structure data is required for recommendation.")

        try:
            response = self._get_client().responses.create(
                model=self._model,
                instructions=build_key_recommendation_instructions(),
                input=build_key_recommendation_input(
                    detected_key=detected_key,
                    song_structure=song_structure,
                    singer_constraint=singer_constraint,
                    song_title=song_title,
                    artist_name=artist_name,
                ),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "key_shift_recommendation",
                        "strict": True,
                        "schema": KEY_RECOMMENDATION_SCHEMA,
                    }
                },
            )
        except Exception as exc:
            raise KeyRecommendationError("OpenAI key recommendation request failed.") from exc

        raw_output = getattr(response, "output_text", None)
        if not raw_output:
            raise KeyRecommendationError("OpenAI returned an empty key recommendation response.")

        try:
            parsed_output = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise KeyRecommendationError(
                "OpenAI returned a non-JSON key recommendation response."
            ) from exc

        self._validate_response(parsed_output)
        return parsed_output

    def _validate_response(self, payload: dict[str, Any]) -> None:
        required_fields = {"primary", "alternatives", "confidence", "reasoning"}
        missing_fields = required_fields.difference(payload.keys())
        if missing_fields:
            missing_list = ", ".join(sorted(missing_fields))
            raise KeyRecommendationError(
                f"OpenAI response is missing required fields: {missing_list}"
            )

        alternatives = payload.get("alternatives", [])
        if not isinstance(alternatives, list) or len(alternatives) != 2:
            raise KeyRecommendationError(
                "Key recommendation response must contain exactly two alternatives."
            )

        labels = {item.get("label") for item in alternatives if isinstance(item, dict)}
        if labels != {"safer", "closer_to_original"}:
            raise KeyRecommendationError(
                "Alternatives must include 'safer' and 'closer_to_original'."
            )

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI()
        return self._client
