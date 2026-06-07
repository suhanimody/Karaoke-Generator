"""Service for extracting tempo and key information from audio."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import librosa
import numpy as np


class AudioAnalysisError(Exception):
    """Raised when audio analysis cannot be completed."""


@dataclass(frozen=True)
class AudioAnalysisResult:
    """Structured output for tempo and key analysis."""

    tempo: float
    key: str

    def to_dict(self) -> dict[str, float | str]:
        """Return a JSON-serializable representation."""
        return asdict(self)


class AudioAnalysisService:
    """Extracts tempo and estimated musical key from an audio file."""

    _PITCH_CLASS_NAMES = (
        "C",
        "C#",
        "D",
        "D#",
        "E",
        "F",
        "F#",
        "G",
        "G#",
        "A",
        "A#",
        "B",
    )

    _MAJOR_PROFILE = np.array(
        [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
        dtype=float,
    )
    _MINOR_PROFILE = np.array(
        [6.33, 2.68, 3.52, 5.38, 2.6, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
        dtype=float,
    )

    def __init__(self, sample_rate: int = 22050) -> None:
        self._sample_rate = sample_rate

    def analyze(self, audio_file_path: str) -> AudioAnalysisResult:
        """
        Analyze an audio file for tempo and key.

        Args:
            audio_file_path: Path to a playable audio file.

        Returns:
            AudioAnalysisResult with tempo in BPM and key as a string.

        Raises:
            AudioAnalysisError: The file is invalid or analysis fails.
        """
        input_path = self._validate_input(audio_file_path)

        try:
            signal, sample_rate = librosa.load(
                path=str(input_path),
                sr=self._sample_rate,
                mono=True,
            )
        except Exception as exc:
            raise AudioAnalysisError(f"Failed to load audio file: {input_path}") from exc

        if signal.size == 0:
            raise AudioAnalysisError("Loaded audio is empty.")

        tempo = self._estimate_tempo(signal=signal, sample_rate=sample_rate)
        key = self._estimate_key(signal=signal, sample_rate=sample_rate)

        return AudioAnalysisResult(tempo=tempo, key=key)

    def analyze_to_dict(self, audio_file_path: str) -> dict[str, float | str]:
        """Analyze audio and return a JSON-ready dictionary."""
        return self.analyze(audio_file_path).to_dict()

    def _estimate_tempo(self, signal: np.ndarray, sample_rate: int) -> float:
        onset_envelope = librosa.onset.onset_strength(y=signal, sr=sample_rate)
        tempo, _ = librosa.beat.beat_track(
            onset_envelope=onset_envelope,
            sr=sample_rate,
        )
        return round(float(tempo), 2)

    def _estimate_key(self, signal: np.ndarray, sample_rate: int) -> str:
        harmonic_signal = librosa.effects.harmonic(signal)
        chroma = librosa.feature.chroma_cqt(y=harmonic_signal, sr=sample_rate)
        pitch_class_energy = chroma.mean(axis=1)

        if np.allclose(pitch_class_energy, 0):
            raise AudioAnalysisError("Unable to estimate key from low-information audio.")

        normalized_energy = self._normalize_vector(pitch_class_energy)
        best_key_name = ""
        best_score = float("-inf")

        for index, pitch_name in enumerate(self._PITCH_CLASS_NAMES):
            major_score = self._correlation_score(
                normalized_energy,
                np.roll(self._MAJOR_PROFILE, index),
            )
            if major_score > best_score:
                best_score = major_score
                best_key_name = f"{pitch_name} major"

            minor_score = self._correlation_score(
                normalized_energy,
                np.roll(self._MINOR_PROFILE, index),
            )
            if minor_score > best_score:
                best_score = minor_score
                best_key_name = f"{pitch_name} minor"

        if not best_key_name:
            raise AudioAnalysisError("Unable to estimate musical key.")

        return best_key_name

    def _correlation_score(
        self,
        pitch_class_energy: np.ndarray,
        profile: np.ndarray,
    ) -> float:
        normalized_profile = self._normalize_vector(profile)
        return float(np.dot(pitch_class_energy, normalized_profile))

    def _normalize_vector(self, values: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(values)
        if norm == 0:
            return values
        return values / norm

    def _validate_input(self, audio_file_path: str) -> Path:
        if not audio_file_path or not audio_file_path.strip():
            raise AudioAnalysisError("An audio file path is required.")

        input_path = Path(audio_file_path).expanduser().resolve()
        if not input_path.exists() or not input_path.is_file():
            raise AudioAnalysisError(f"Audio file does not exist: {input_path}")

        return input_path
