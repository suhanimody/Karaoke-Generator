"""Service for downloading YouTube audio and converting it to WAV."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AUDIO_STORAGE_DIR = PROJECT_ROOT / "data" / "audio"
SUPPORTED_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


class AudioExtractionError(Exception):
    """Raised when audio extraction fails for any non-timeout reason."""


class InvalidYouTubeUrlError(AudioExtractionError):
    """Raised when the provided URL is not a valid YouTube URL."""


class AudioExtractionTimeoutError(AudioExtractionError):
    """Raised when yt-dlp does not finish before the timeout."""


class YouTubeAudioExtractionService:
    """Downloads the best available YouTube audio and converts it to WAV."""

    def __init__(
        self,
        storage_dir: Path | None = None,
        timeout_seconds: int = 300,
    ) -> None:
        self._storage_dir = (storage_dir or DEFAULT_AUDIO_STORAGE_DIR).resolve()
        self._timeout_seconds = timeout_seconds
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def extract_audio(self, youtube_url: str) -> str:
        """
        Download a YouTube video's audio track as WAV and return the local path.

        Args:
            youtube_url: A full YouTube watch/share URL.

        Returns:
            The local WAV file path as a string.

        Raises:
            InvalidYouTubeUrlError: The URL is malformed or not a YouTube URL.
            AudioExtractionTimeoutError: Extraction exceeded the configured timeout.
            AudioExtractionError: yt-dlp failed or the output file was not created.
        """
        normalized_url = self._validate_youtube_url(youtube_url)
        output_stem = self._storage_dir / uuid4().hex
        expected_output_path = output_stem.with_suffix(".wav")

        command = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "--format",
            "bestaudio/best",
            "--extract-audio",
            "--audio-format",
            "wav",
            "--output",
            str(output_stem) + ".%(ext)s",
            normalized_url,
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
            self._cleanup_partial_outputs(output_stem)
            raise AudioExtractionTimeoutError(
                f"Audio extraction timed out after {self._timeout_seconds} seconds."
            ) from exc
        except OSError as exc:
            self._cleanup_partial_outputs(output_stem)
            raise AudioExtractionError(
                "Failed to start yt-dlp. Ensure yt-dlp and ffmpeg are installed."
            ) from exc

        if completed_process.returncode != 0:
            self._cleanup_partial_outputs(output_stem)
            stderr = (completed_process.stderr or "").strip()
            stdout = (completed_process.stdout or "").strip()
            error_details = stderr or stdout or "yt-dlp failed without an error message."
            raise AudioExtractionError(f"Audio extraction failed: {error_details}")

        if not expected_output_path.exists():
            self._cleanup_partial_outputs(output_stem)
            raise AudioExtractionError(
                f"yt-dlp completed but expected output was not found: {expected_output_path}"
            )

        return str(expected_output_path)

    def _validate_youtube_url(self, youtube_url: str) -> str:
        if not youtube_url or not youtube_url.strip():
            raise InvalidYouTubeUrlError("A YouTube URL is required.")

        parsed_url = urlparse(youtube_url.strip())
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise InvalidYouTubeUrlError("The provided URL is not a valid HTTP(S) URL.")

        hostname = parsed_url.netloc.lower().split(":")[0]
        if hostname not in SUPPORTED_YOUTUBE_HOSTS:
            raise InvalidYouTubeUrlError("The provided URL is not a supported YouTube link.")

        return parsed_url.geturl()

    def _cleanup_partial_outputs(self, output_stem: Path) -> None:
        for path in self._storage_dir.glob(f"{output_stem.name}*"):
            if path.is_file():
                path.unlink(missing_ok=True)
