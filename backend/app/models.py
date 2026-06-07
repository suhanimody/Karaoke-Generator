"""Shared API models for the FastAPI application."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class AudioExtractionRequest(BaseModel):
    youtube_url: HttpUrl


class AudioExtractionResponse(BaseModel):
    file_path: str


class AudioAnalysisRequest(BaseModel):
    audio_file_path: str = Field(min_length=1)


class AudioAnalysisResponse(BaseModel):
    tempo: float
    key: str


class SongStructureRequest(BaseModel):
    lyrics: str = Field(min_length=1)
    tempo: float = Field(gt=0)
    key: str = Field(min_length=1)
    song_title: str | None = None
    artist_name: str | None = None


class KeyRecommendationRequest(BaseModel):
    detected_key: str = Field(min_length=1)
    song_structure: dict[str, Any]
    singer_constraint: str = Field(
        default="Singer struggles with high notes.",
        min_length=1,
    )
    song_title: str | None = None
    artist_name: str | None = None


class SectionTimestampRequest(BaseModel):
    song_structure: dict[str, Any]
    duration_seconds: float | None = Field(default=None, gt=0)
    audio_file_path: str | None = None
    lyrics: str | None = None


class KeyRecommendationAlternativeResponse(BaseModel):
    label: Literal["safer", "closer_to_original"]
    shift: str
    reason: str


class KeyRecommendationResponse(BaseModel):
    primary: str
    alternatives: list[KeyRecommendationAlternativeResponse]
    confidence: float
    reasoning: str


class SongStructureSectionResponse(BaseModel):
    label: str
    index: int
    summary: str
    start_line: int
    end_line: int
    confidence: float


class SongStructureEnergyResponse(BaseModel):
    section_index: int
    label: str
    energy_level: str
    reason: str


class SongStructureDifficultyResponse(BaseModel):
    section_index: int
    label: str
    difficulty_level: str
    reason: str


class SongStructureResponse(BaseModel):
    sections: list[SongStructureSectionResponse]
    energy_progression: list[SongStructureEnergyResponse]
    difficult_sections: list[SongStructureDifficultyResponse]
    overall_summary: str


class TimestampedSectionResponse(BaseModel):
    section: str
    start: float
    end: float
    confidence: float
