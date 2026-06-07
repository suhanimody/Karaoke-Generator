"""Service for mapping song structure into approximate playback timestamps."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import librosa


class SectionTimestampMappingError(Exception):
    """Raised when structure-to-timestamp mapping fails."""


@dataclass(frozen=True)
class TimestampedSection:
    """Approximate playback metadata for one section."""

    section: str
    start: float
    end: float
    confidence: float

    def to_dict(self) -> dict[str, float | str]:
        """Return a JSON-serializable representation."""
        return asdict(self)


class SectionTimestampMappingService:
    """Map structure labels into approximate playback timestamps."""

    def map_sections(
        self,
        *,
        song_structure: dict[str, Any],
        duration_seconds: float | None = None,
        audio_file_path: str | None = None,
        lyrics: str | None = None,
    ) -> list[dict[str, float | str]]:
        """
        Convert line-based structure metadata into timestamped playback sections.

        Args:
            song_structure: Structure JSON containing a `sections` array.
            duration_seconds: Known song duration in seconds.
            audio_file_path: Optional audio path used to derive song duration.
            lyrics: Optional full lyrics text to improve line-based timing.

        Returns:
            A list of timestamped section dictionaries ordered by playback time.
        """
        sections = self._extract_sections(song_structure)
        resolved_duration = self._resolve_duration(
            duration_seconds=duration_seconds,
            audio_file_path=audio_file_path,
        )
        total_line_count = self._resolve_total_line_count(sections=sections, lyrics=lyrics)

        timestamped_sections: list[TimestampedSection] = []
        for section in sections:
            start_line = self._sanitize_line_number(section.get("start_line"), minimum=1)
            end_line = self._sanitize_line_number(section.get("end_line"), minimum=start_line)

            start_seconds = self._line_to_seconds(
                line_number=start_line,
                total_line_count=total_line_count,
                duration_seconds=resolved_duration,
            )
            end_seconds = self._line_to_seconds(
                line_number=end_line + 1,
                total_line_count=total_line_count,
                duration_seconds=resolved_duration,
            )

            confidence = self._sanitize_confidence(section.get("confidence"))
            timestamped_sections.append(
                TimestampedSection(
                    section=str(section["label"]),
                    start=round(start_seconds, 2),
                    end=round(min(end_seconds, resolved_duration), 2),
                    confidence=confidence,
                )
            )

        return self._normalize_boundaries(timestamped_sections, resolved_duration)

    def _extract_sections(self, song_structure: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(song_structure, dict):
            raise SectionTimestampMappingError("Song structure payload must be a dictionary.")

        raw_sections = song_structure.get("sections")
        if not isinstance(raw_sections, list) or not raw_sections:
            raise SectionTimestampMappingError("Song structure must contain a non-empty sections array.")

        normalized_sections: list[dict[str, Any]] = []
        for section in raw_sections:
            if not isinstance(section, dict):
                raise SectionTimestampMappingError("Each section must be an object.")
            if "label" not in section:
                raise SectionTimestampMappingError("Each section must include a label.")
            normalized_sections.append(section)

        return normalized_sections

    def _resolve_duration(
        self,
        *,
        duration_seconds: float | None,
        audio_file_path: str | None,
    ) -> float:
        if duration_seconds is not None:
            if duration_seconds <= 0:
                raise SectionTimestampMappingError("Duration must be a positive number.")
            return float(duration_seconds)

        if not audio_file_path or not audio_file_path.strip():
            raise SectionTimestampMappingError(
                "Provide either duration_seconds or audio_file_path for timestamp mapping."
            )

        input_path = Path(audio_file_path).expanduser().resolve()
        if not input_path.exists() or not input_path.is_file():
            raise SectionTimestampMappingError(f"Audio file does not exist: {input_path}")

        try:
            duration = librosa.get_duration(path=str(input_path))
        except Exception as exc:
            raise SectionTimestampMappingError(
                f"Failed to determine audio duration from file: {input_path}"
            ) from exc

        if duration <= 0:
            raise SectionTimestampMappingError("Audio duration must be greater than zero.")

        return float(duration)

    def _resolve_total_line_count(
        self,
        *,
        sections: list[dict[str, Any]],
        lyrics: str | None,
    ) -> int:
        if lyrics and lyrics.strip():
            lyric_lines = [line.strip() for line in lyrics.splitlines() if line.strip()]
            if lyric_lines:
                return len(lyric_lines)

        max_end_line = 0
        for section in sections:
            end_line = section.get("end_line")
            if isinstance(end_line, int) and end_line > max_end_line:
                max_end_line = end_line

        if max_end_line > 0:
            return max_end_line

        return len(sections)

    def _line_to_seconds(
        self,
        *,
        line_number: int,
        total_line_count: int,
        duration_seconds: float,
    ) -> float:
        safe_total_line_count = max(total_line_count, 1)
        clamped_line_number = min(max(line_number, 1), safe_total_line_count + 1)
        progress_ratio = (clamped_line_number - 1) / safe_total_line_count
        return progress_ratio * duration_seconds

    def _sanitize_line_number(self, value: Any, *, minimum: int) -> int:
        if isinstance(value, int) and value >= minimum:
            return value
        return minimum

    def _sanitize_confidence(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return round(max(0.0, min(float(value), 1.0)), 2)
        return 0.5

    def _normalize_boundaries(
        self,
        sections: list[TimestampedSection],
        duration_seconds: float,
    ) -> list[dict[str, float | str]]:
        normalized: list[dict[str, float | str]] = []

        for index, section in enumerate(sections):
            start_seconds = section.start
            end_seconds = section.end

            if index > 0:
                previous_end = normalized[index - 1]["end"]
                start_seconds = max(float(previous_end), start_seconds)

            if index < len(sections) - 1:
                next_start = sections[index + 1].start
                end_seconds = min(end_seconds, next_start)
            else:
                end_seconds = duration_seconds

            if end_seconds < start_seconds:
                end_seconds = start_seconds

            normalized.append(
                {
                    "section": section.section,
                    "start": round(start_seconds, 2),
                    "end": round(end_seconds, 2),
                    "confidence": section.confidence,
                }
            )

        return normalized
