"""FastAPI entrypoint for the AI Karaoke Performance Assistant backend."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    AudioAnalysisRequest,
    AudioAnalysisResponse,
    AudioExtractionRequest,
    AudioExtractionResponse,
    KeyRecommendationRequest,
    KeyRecommendationResponse,
    SectionTimestampRequest,
    SongStructureRequest,
    SongStructureResponse,
    TimestampedSectionResponse,
)
from .services import (
    AudioAnalysisError,
    AudioAnalysisService,
    AudioExtractionError,
    KeyRecommendationError,
    KeyRecommendationService,
    SectionTimestampMappingError,
    SectionTimestampMappingService,
    SongStructureAnalysisError,
    SongStructureAnalysisService,
    YouTubeAudioExtractionService,
)


app = FastAPI(
    title="AI Karaoke Performance Assistant API",
    version="0.1.0",
    description="Backend APIs for karaoke extraction, analysis, and performance prep.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

audio_extraction_service = YouTubeAudioExtractionService()
audio_analysis_service = AudioAnalysisService()
song_structure_service = SongStructureAnalysisService()
key_recommendation_service = KeyRecommendationService()
section_timestamp_service = SectionTimestampMappingService()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/extract-audio", response_model=AudioExtractionResponse)
def extract_audio(payload: AudioExtractionRequest) -> AudioExtractionResponse:
    try:
        file_path = audio_extraction_service.extract_audio(str(payload.youtube_url))
    except AudioExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AudioExtractionResponse(file_path=file_path)


@app.post("/api/analyze-audio", response_model=AudioAnalysisResponse)
def analyze_audio(payload: AudioAnalysisRequest) -> AudioAnalysisResponse:
    try:
        result = audio_analysis_service.analyze(payload.audio_file_path)
    except AudioAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AudioAnalysisResponse(tempo=result.tempo, key=result.key)


@app.post("/api/song-structure", response_model=SongStructureResponse)
def analyze_song_structure(payload: SongStructureRequest) -> SongStructureResponse:
    try:
        result = song_structure_service.analyze(
            lyrics=payload.lyrics,
            tempo=payload.tempo,
            key=payload.key,
            song_title=payload.song_title,
            artist_name=payload.artist_name,
        )
    except SongStructureAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SongStructureResponse.model_validate(result)


@app.post("/api/key-recommendation", response_model=KeyRecommendationResponse)
def recommend_key_shift(
    payload: KeyRecommendationRequest,
) -> KeyRecommendationResponse:
    try:
        result = key_recommendation_service.recommend(
            detected_key=payload.detected_key,
            song_structure=payload.song_structure,
            singer_constraint=payload.singer_constraint,
            song_title=payload.song_title,
            artist_name=payload.artist_name,
        )
    except KeyRecommendationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return KeyRecommendationResponse.model_validate(result)


@app.post(
    "/api/section-timestamps",
    response_model=list[TimestampedSectionResponse],
)
def map_section_timestamps(
    payload: SectionTimestampRequest,
) -> list[TimestampedSectionResponse]:
    try:
        result = section_timestamp_service.map_sections(
            song_structure=payload.song_structure,
            duration_seconds=payload.duration_seconds,
            audio_file_path=payload.audio_file_path,
            lyrics=payload.lyrics,
        )
    except SectionTimestampMappingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [TimestampedSectionResponse.model_validate(item) for item in result]
