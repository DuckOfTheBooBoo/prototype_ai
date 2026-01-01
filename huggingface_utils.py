"""
HuggingFace utilities for downloading model artifacts.

This module provides functions to download model artifacts from HuggingFace Hub
and cache them locally for use by the FraudDetector.
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Optional
from huggingface_hub import hf_hub_download, HfApi

logger = logging.getLogger(__name__)


class HuggingFaceDownloader:
    """Handles downloading and caching of model artifacts from HuggingFace."""

    def __init__(
        self,
        repo_id: str,
        cache_dir: Optional[str] = None,
        force_download: bool = False
    ):
        """
        Initialize the HuggingFace downloader.

        Args:
            repo_id: The HuggingFace repository ID (e.g., "username/fraud-detection-model")
            cache_dir: Local directory to cache downloaded files. If None, uses default cache.
            force_download: If True, always re-download files even if cached.
        """
        self.repo_id = repo_id
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), ".model_cache")
        self.force_download = force_download

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

        # Artifacts that need to be downloaded
        self.artifacts = [
            "artifact_model.pkl",
            "artifact_encoder.pkl",
            "artifact_card1_stats.pkl",
            "artifact_cat_cols.pkl",
            "artifact_columns.pkl"
        ]

    def _get_local_path(self, filename: str) -> str:
        """Get the local cache path for a file."""
        return os.path.join(self.cache_dir, filename)

    def _get_file_hash(self, filepath: str) -> str:
        """Get MD5 hash of a file for cache validation."""
        if not os.path.exists(filepath):
            return None

        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def download_artifact(self, filename: str) -> str:
        """
        Download a single artifact file from HuggingFace.

        Args:
            filename: The filename to download (e.g., "artifact_model.pkl")

        Returns:
            The local path to the downloaded file.
        """
        local_path = self._get_local_path(filename)

        # Check cache unless force_download is True
        if os.path.exists(local_path) and not self.force_download:
            logger.info(f"Using cached file: {filename}")
            return local_path

        logger.info(f"Downloading {filename} from HuggingFace...")

        try:
            downloaded_path = hf_hub_download(
                repo_id=self.repo_id,
                filename=filename,
                repo_type="model",
                cache_dir=self.cache_dir,
                force_download=self.force_download
            )

            # Copy to our cache location if it's different
            if downloaded_path != local_path:
                import shutil
                shutil.copy2(downloaded_path, local_path)
                logger.info(f"Cached {filename} to {local_path}")

            return local_path

        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")
            # If cached version exists, use it anyway
            if os.path.exists(local_path):
                logger.warning(f"Using existing cached file despite error: {filename}")
                return local_path
            raise

    def download_all_artifacts(self) -> dict:
        """
        Download all required artifacts from HuggingFace.

        Returns:
            Dictionary mapping filenames to local paths.
        """
        downloaded = {}

        for filename in self.artifacts:
            try:
                path = self.download_artifact(filename)
                downloaded[filename] = path
                logger.info(f"Successfully downloaded: {filename}")
            except Exception as e:
                logger.error(f"Failed to download {filename}: {e}")
                raise RuntimeError(f"Failed to download required artifact: {filename}")

        return downloaded

    def verify_artifacts(self) -> bool:
        """
        Verify that all required artifacts are available.

        Returns:
            True if all artifacts are available, False otherwise.
        """
        for filename in self.artifacts:
            local_path = self._get_local_path(filename)
            if not os.path.exists(local_path):
                logger.warning(f"Missing artifact: {filename}")
                return False

        return True

    def get_artifact_path(self, filename: str) -> str:
        """
        Get the path to a cached artifact, downloading if necessary.

        Args:
            filename: The filename to get

        Returns:
            The local path to the artifact
        """
        return self.download_artifact(filename)


def get_huggingface_downloader(
    repo_id: Optional[str] = None,
    force_download: bool = False
) -> HuggingFaceDownloader:
    """
    Factory function to create a HuggingFaceDownloader.

    Args:
        repo_id: The HuggingFace repository ID. If None, reads from environment variable.
        force_download: If True, always re-download files.

    Returns:
        Configured HuggingFaceDownloader instance.

    Raises:
        ValueError: If no repository ID is provided and HF_REPO_ID env var is not set.
    """
    if repo_id is None:
        repo_id = os.environ.get("HF_REPO_ID")
        if not repo_id:
            raise ValueError(
                "No HuggingFace repository ID provided. "
                "Either pass repo_id or set HF_REPO_ID environment variable."
            )

    return HuggingFaceDownloader(
        repo_id=repo_id,
        force_download=force_download
    )


def download_models_from_huggingface(repo_id: str, output_dir: str = "./artifacts") -> bool:
    """
    Convenience function to download all model artifacts from HuggingFace.

    Args:
        repo_id: The HuggingFace repository ID
        output_dir: The output directory for artifacts

    Returns:
        True if successful, False otherwise.
    """
    try:
        downloader = HuggingFaceDownloader(repo_id=repo_id, cache_dir=output_dir)
        artifacts = downloader.download_all_artifacts()

        logger.info(f"Successfully downloaded {len(artifacts)} artifacts to {output_dir}")
        return True

    except Exception as e:
        logger.error(f"Failed to download models from HuggingFace: {e}")
        return False


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python huggingface_utils.py <repo_id>")
        print("Example: python huggingface_utils.py username/fraud-detection-model")
        sys.exit(1)

    repo_id = sys.argv[1]
    success = download_models_from_huggingface(repo_id)

    if success:
        print("Download complete!")
    else:
        print("Download failed!")
        sys.exit(1)
