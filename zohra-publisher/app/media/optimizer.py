"""
Zohra — Image Optimizer & Responsive Formatter.

Processes raw image outputs:
- Strips EXIF metadata and normalizes orientation.
- Encodes modern WebP files with high visual fidelity.
- Generates responsive dimension variants (1536w, 1200w, 768w, 480w).
- Computes SHA-256 cryptographic and dHash perceptual hashes.
- Generates clean SEO filenames and descriptive ALT text.
"""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import re
from PIL import Image, ImageOps

from app.core.config import get_settings
from app.core.logging import get_logger
from app.media.models import OptimizationResult, ResponsiveVariant, VisualAnalysis

logger = get_logger("media.optimizer")


class ImageOptimizer:
    """Production image compression, resizing, hashing, and metadata generation."""

    @classmethod
    def compute_sha256(cls, data: bytes) -> str:
        """Computes SHA-256 cryptographic hash of image bytes."""
        return hashlib.sha256(data).hexdigest()

    @classmethod
    def compute_perceptual_hash(cls, img: Image.Image) -> str:
        """Computes 64-bit difference hash (dHash) for visual similarity comparison."""
        # Convert to grayscale and resize to 9x8
        gray = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(gray.getdata())
        difference = []
        for row in range(8):
            for col in range(8):
                idx = row * 9 + col
                difference.append(pixels[idx] > pixels[idx + 1])
        # Convert 64 boolean values to 16 hex chars
        decimal_val = 0
        hex_val = []
        for idx, val in enumerate(difference):
            if val:
                decimal_val += 2 ** (idx % 4)
            if (idx % 4) == 3:
                hex_val.append(hex(decimal_val)[2:])
                decimal_val = 0
        return "".join(hex_val)

    @classmethod
    def generate_seo_filename(cls, title: str) -> str:
        """
        Creates clean, lowercase, hyphen-separated SEO-friendly filename without keyword stuffing.
        Example: 'students-using-ai-study-assistant.webp'
        """
        clean = re.sub(r"[^\w\s-]", "", title.lower())
        hyphenated = re.sub(r"[-\s]+", "-", clean).strip("-")[:55]
        return f"{hyphenated}.webp"

    @classmethod
    def generate_alt_text(cls, analysis: VisualAnalysis) -> str:
        """
        Generates descriptive, accessible ALT text accurately describing the visual representation.
        Avoids repetitive keyword-stuffing.
        """
        subject = analysis.primary_subject
        # E.g. "Practical guide on student study workflows with digital assistive tools"
        return f"Editorial visual representing {subject.lower()}"

    @classmethod
    def optimize(
        cls,
        raw_bytes: bytes,
        title: str,
        analysis: VisualAnalysis,
        storage_subdir: str = "media/articles",
    ) -> OptimizationResult:
        """
        Optimizes the image, generates WebP variants, and saves them to local storage.
        """
        settings = get_settings()
        storage_root = Path(getattr(settings, "STORAGE_DIR", "./storage"))
        target_dir = storage_root / storage_subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Open and normalize image
        with Image.open(io.BytesIO(raw_bytes)) as pil_img:
            # Auto-orient based on EXIF
            pil_img = ImageOps.exif_transpose(pil_img)
            if pil_img.mode in ("RGBA", "P"):
                pil_img = pil_img.convert("RGB")

            # Compute perceptual hash before resizing
            p_hash = cls.compute_perceptual_hash(pil_img)

            base_filename = cls.generate_seo_filename(title)
            filename_stem = Path(base_filename).stem
            alt_text = cls.generate_alt_text(analysis)

            # Responsive widths preserving 16:9 aspect ratio
            # Standard dimensions: 1536x864 (hero), 1200x675, 768x432, 480x270
            variant_specs = [
                ("1536w", 1536, 864),
                ("1200w", 1200, 675),
                ("768w", 768, 432),
                ("480w", 480, 270),
            ]

            responsive_variants: list[ResponsiveVariant] = []
            primary_bytes = b""
            primary_width = 1536
            primary_height = 864

            for label, w, h in variant_specs:
                # Center-crop to the target 16:9 frame, then downscale.
                # Using crop-then-resize (instead of a plain resize) means a
                # provider returning a square or off-ratio image is framed
                # rather than stretched out of shape.
                resized = ImageOps.fit(
                    pil_img,
                    (w, h),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
                buf = io.BytesIO()
                resized.save(buf, format="WEBP", quality=85, method=6)
                var_bytes = buf.getvalue()

                variant_filename = f"{filename_stem}-{label}.webp" if label != "1536w" else f"{filename_stem}.webp"
                var_path = target_dir / variant_filename
                var_path.write_bytes(var_bytes)

                public_url = f"/storage/{storage_subdir}/{variant_filename}"
                responsive_variants.append(
                    ResponsiveVariant(
                        label=label,
                        width=w,
                        height=h,
                        file_size_bytes=len(var_bytes),
                        local_path=str(var_path),
                        public_url=public_url,
                    )
                )

                if label == "1536w":
                    primary_bytes = var_bytes
                    primary_width = w
                    primary_height = h

            if not primary_bytes:
                primary_bytes = raw_bytes

            content_hash = cls.compute_sha256(primary_bytes)
            primary_path = target_dir / f"{filename_stem}.webp"
            public_primary_url = f"/storage/{storage_subdir}/{filename_stem}.webp"

            return OptimizationResult(
                primary_bytes=primary_bytes,
                content_hash=content_hash,
                perceptual_hash=p_hash,
                width=primary_width,
                height=primary_height,
                file_size_bytes=len(primary_bytes),
                mime_type="image/webp",
                filename=f"{filename_stem}.webp",
                alt_text=alt_text,
                caption=f"Visual representation of {title}",
                local_storage_path=str(primary_path),
                public_url=public_primary_url,
                responsive_variants=responsive_variants,
            )
