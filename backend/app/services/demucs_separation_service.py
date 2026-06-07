"""Service for separating vocals and instrumental stems with Demucs."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SEPARATION_STORAGE_DIR = PROJECT_ROOT / "data" / "separated"


class AudioSeparationError(Exception):
    """Raised when Demucs separation fails for any non-timeout reason."""


class AudioSeparationTimeoutError(AudioSeparationError):
    """Raised when Demucs does not finish before the timeout."""


@dataclass(frozen=True)
class SeparationResult:
    """Normalized output paths for a Demucs separation run."""

    output_dir: str
    vocals_path: str
    instrumental_path: str


class DemucsSeparationService:
    """Separates a WAV file into vocals and instrumental stems with Demucs."""

    def __init__(
        self,
        storage_dir: Path | None = None,
        timeout_seconds: int = 900,
        model_name: str = "htdemucs",
    ) -> None:
        self._storage_dir = (storage_dir or DEFAULT_SEPARATION_STORAGE_DIR).resolve()
        self._timeout_seconds = timeout_seconds
        self._model_name = model_name
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def separate(self, wav_file_path: str) -> SeparationResult:
        """
        Separate a WAV file into vocals and instrumental stems.

        Args:
            wav_file_path: Path to the input WAV file.

        Returns:
            SeparationResult containing stable local output paths.

        Raises:
            AudioSeparationError: Input validation or Demucs execution failed.
            AudioSeparationTimeoutError: Demucs exceeded the configured timeout.
        """
        input_path = self._validate_input(wav_file_path)
        output_dir = self._storage_dir / f"{input_path.stem}-{uuid4().hex[:8]}"
        demucs_work_dir = output_dir / "_demucs_raw"
        output_dir.mkdir(parents=True, exist_ok=True)
        demucs_work_dir.mkdir(parents=True, exist_ok=True)

        command = [
            sys.executable,
            "-m",
            "demucs.separate",
            "--two-stems",
            "vocals",
            "--out",
            str(demucs_work_dir),
            "-n",
            self._model_name,
            str(input_path),
        ]

        try:
            completed_process = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            self._cleanup_output_dir(output_dir)
            raise AudioSeparationTimeoutError(
                f"Audio separation timed out after {self._timeout_seconds} seconds."
            ) from exc
        except OSError as exc:
            self._cleanup_output_dir(output_dir)
            raise AudioSeparationError(
                "Failed to start Demucs. Ensure demucs and its dependencies are installed."
            ) from exc

        if completed_process.returncode != 0:
            self._cleanup_output_dir(output_dir)
            stderr = (completed_process.stderr or "").strip()
            stdout = (completed_process.stdout or "").strip()
            error_details = stderr or stdout or "Demucs failed without an error message."
            raise AudioSeparationError(f"Audio separation failed: {error_details}")

        raw_stem_dir = demucs_work_dir / self._model_name / input_path.stem
        vocals_source = raw_stem_dir / "vocals.wav"
        instrumental_source = raw_stem_dir / "no_vocals.wav"
        vocals_target = output_dir / "vocals.wav"
        instrumental_target = output_dir / "instrumental.wav"

        if not vocals_source.exists() or not instrumental_source.exists():
            self._cleanup_output_dir(output_dir)
            raise AudioSeparationError(
                "Demucs completed but expected stem files were not found."
            )

        shutil.move(str(vocals_source), str(vocals_target))
        shutil.move(str(instrumental_source), str(instrumental_target))
        shutil.rmtree(demucs_work_dir, ignore_errors=True)

        return SeparationResult(
            output_dir=str(output_dir),
            vocals_path=str(vocals_target),
            instrumental_path=str(instrumental_target),
        )

    def _validate_input(self, wav_file_path: str) -> Path:
        if not wav_file_path or not wav_file_path.strip():
            raise AudioSeparationError("A WAV file path is required.")

        input_path = Path(wav_file_path).expanduser().resolve()
        if not input_path.exists() or not input_path.is_file():
            raise AudioSeparationError(f"Input WAV file does not exist: {input_path}")

        if input_path.suffix.lower() != ".wav":
            raise AudioSeparationError("Demucs separation requires a WAV input file.")

        return input_path

    def _cleanup_output_dir(self, output_dir: Path) -> None:
        shutil.rmtree(output_dir, ignore_errors=True)
