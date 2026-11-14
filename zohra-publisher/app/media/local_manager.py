"""
Zohra — Local Generative Image Model Manager.

Manages loading, optimization, thread/concurrency locking, memory recovery,
and execution for local text-to-image diffusion pipelines.
"""

from __future__ import annotations

import asyncio
import gc
import io
import os
import threading
import time
from typing import Any
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import ZohraError
from app.core.logging import get_logger

logger = get_logger("media.local_manager")

_manager_instance: LocalImageModelManager | None = None
_manager_lock = threading.Lock()


class LocalImageModelManager:
    """Singleton manager for local text-to-image diffusion models."""

    def __init__(self) -> None:
        self.pipeline: Any = None
        self.model_id: str | None = None
        self.device: str = "cpu"
        self.dtype: Any = None
        self._lock: asyncio.Lock | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._is_loading: bool = False
        self._load_error: str | None = None
        self._last_used: float = 0.0

        # Hardware detection
        self._detect_hardware()

    def _detect_hardware(self) -> None:
        settings = get_settings()
        cfg_dev = getattr(settings, "LOCAL_IMAGE_DEVICE", "auto").lower()

        try:
            import torch
            if cfg_dev == "cuda" and torch.cuda.is_available():
                self.device = "cuda"
                self.dtype = torch.float16
            elif cfg_dev == "auto" and torch.cuda.is_available():
                # Check compute capability >= 5.0
                cc = torch.cuda.get_device_capability(0)
                if cc[0] >= 5:
                    self.device = "cuda"
                    self.dtype = torch.float16
                else:
                    self.device = "cpu"
                    self.dtype = torch.float32
            else:
                self.device = "cpu"
                self.dtype = torch.float32

            # Set thread limit for CPU inference to avoid pinning all cores
            if self.device == "cpu":
                threads = getattr(settings, "LOCAL_IMAGE_THREAD_LIMIT", 4)
                torch.set_num_threads(max(1, threads))
        except ImportError:
            self.device = "cpu"
            self.dtype = None

        logger.info(f"LocalImageModelManager initialized: device={self.device}, dtype={self.dtype}")

    @property
    def lock(self) -> asyncio.Lock:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if self._lock is None or getattr(self, "_lock_loop", None) != loop:
            self._lock = asyncio.Lock()
            self._lock_loop = loop
        return self._lock

    @property
    def semaphore(self) -> asyncio.Semaphore:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if self._semaphore is None or getattr(self, "_sem_loop", None) != loop:
            settings = get_settings()
            max_concurrent = max(1, getattr(settings, "LOCAL_IMAGE_MAX_CONCURRENT_JOBS", 1))
            self._semaphore = asyncio.Semaphore(max_concurrent)
            self._sem_loop = loop
        return self._semaphore


    async def get_pipeline(self) -> Any:
        """Lazily loads and returns the configured diffusion pipeline."""
        if self.pipeline is not None:
            self._last_used = time.time()
            return self.pipeline

        async with self.lock:
            if self.pipeline is not None:
                return self.pipeline


            settings = get_settings()
            model_id = getattr(settings, "LOCAL_IMAGE_MODEL_ID", "stabilityai/sd-turbo")
            self._is_loading = True
            self._load_error = None

            logger.info(f"Loading local generative model '{model_id}' on {self.device}...")
            start_t = time.time()

            try:
                import torch
                from diffusers import AutoPipelineForText2Image

                pipe = await asyncio.to_thread(
                    self._load_pipeline_sync,
                    model_id,
                    self.device,
                    self.dtype,
                )

                self.pipeline = pipe
                self.model_id = model_id
                self._last_used = time.time()
                elapsed = time.time() - start_t
                logger.info(f"Local generative model '{model_id}' loaded successfully in {elapsed:.2f}s")
                return self.pipeline

            except Exception as e:
                self._load_error = str(e)
                logger.error(f"Failed to load local image model '{model_id}': {e}", exc_info=True)
                raise ZohraError(f"Failed to load local image model: {e}", code="MODEL_LOAD_FAILED") from e
            finally:
                self._is_loading = False

    def _load_pipeline_sync(self, model_id: str, device: str, dtype: Any) -> Any:
        import torch
        from diffusers import AutoPipelineForText2Image

        load_kwargs: dict[str, Any] = {}
        if dtype is not None and device != "cpu":
            load_kwargs["torch_dtype"] = dtype

        try:
            pipe = AutoPipelineForText2Image.from_pretrained(model_id, **load_kwargs)
        except Exception:
            # Fallback to float32
            pipe = AutoPipelineForText2Image.from_pretrained(model_id)

        pipe = pipe.to(device)

        # Apply memory optimizations
        if hasattr(pipe, "enable_attention_slicing"):
            pipe.enable_attention_slicing()
        if hasattr(pipe, "enable_vae_slicing"):
            pipe.enable_vae_slicing()

        return pipe

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str | None = None,
        width: int = 512,
        height: int = 512,
        steps: int = 1,
        guidance_scale: float = 0.0,
        seed: int | None = None,
    ) -> tuple[bytes, dict[str, Any]]:
        """
        Executes bounded, concurrency-safe image generation.
        Returns: (png_image_bytes, metadata_dict)
        """
        async with self.semaphore:
            pipe = await self.get_pipeline()
            settings = get_settings()

            # Ensure dimensions are multiples of 8 for diffusion latent spaces
            gen_width = (width // 8) * 8
            gen_height = (height // 8) * 8

            import torch

            actual_seed = seed if seed is not None else int(time.time() * 1000) % (2**31 - 1)
            generator = torch.Generator(device=self.device).manual_seed(actual_seed)

            logger.info(
                f"Starting local image generation: {gen_width}x{gen_height}, steps={steps}, seed={actual_seed}"
            )
            t0 = time.time()

            try:
                result = await asyncio.to_thread(
                    self._generate_sync,
                    pipe,
                    prompt,
                    negative_prompt,
                    gen_width,
                    gen_height,
                    steps,
                    guidance_scale,
                    generator,
                )
                duration = time.time() - t0

                # Convert PIL image to PNG bytes
                buf = io.BytesIO()
                result.images[0].save(buf, format="PNG")
                raw_bytes = buf.getvalue()

                metadata = {
                    "provider": "local_ai",
                    "model": self.model_id,
                    "device": self.device,
                    "seed": actual_seed,
                    "steps": steps,
                    "guidance_scale": guidance_scale,
                    "generation_duration_sec": round(duration, 3),
                    "native_width": gen_width,
                    "native_height": gen_height,
                }

                logger.info(f"Local image generation complete: {len(raw_bytes)} bytes in {duration:.2f}s")

                # Optional unload after generation for low-spec hosts
                if getattr(settings, "LOCAL_IMAGE_UNLOAD_AFTER_GENERATION", False):
                    await self.unload()

                return raw_bytes, metadata

            except (torch.cuda.OutOfMemoryError if hasattr(torch.cuda, "OutOfMemoryError") else MemoryError, MemoryError) as oom:
                logger.error(f"Local generative image generation encountered Out-Of-Memory: {oom}")
                await self.recover_from_oom()
                raise ZohraError("Local image generation ran out of memory", code="LOCAL_IMAGE_OOM") from oom

            except Exception as e:
                logger.error(f"Local image generation failed: {e}", exc_info=True)
                raise ZohraError(f"Local image generation failed: {e}", code="GENERATION_FAILED") from e

    def _generate_sync(
        self,
        pipe: Any,
        prompt: str,
        negative_prompt: str | None,
        width: int,
        height: int,
        steps: int,
        guidance: float,
        generator: Any,
    ) -> Any:
        import torch

        kwargs: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
            "generator": generator,
        }
        if negative_prompt:
            kwargs["negative_prompt"] = negative_prompt

        with torch.inference_mode():
            return pipe(**kwargs)

    async def recover_from_oom(self) -> None:
        """Safely cleans device cache and forces garbage collection on memory pressure."""
        logger.warning("Executing OOM recovery on local model manager...")
        await self.unload()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except Exception:
            pass
        gc.collect()

    async def unload(self) -> None:
        """Unloads the pipeline and frees memory."""
        async with self.lock:
            if self.pipeline is not None:

                logger.info("Unloading local diffusion pipeline from memory...")
                del self.pipeline
                self.pipeline = None
                self.model_id = None
                gc.collect()
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass

    def get_health(self) -> dict[str, Any]:
        """Returns runtime health and availability status."""
        settings = get_settings()
        status = "AVAILABLE"
        if self._is_loading:
            status = "LOADING"
        elif self._load_error:
            status = "DEGRADED"

        return {
            "provider": "local_ai",
            "status": status,
            "model": self.model_id or getattr(settings, "LOCAL_IMAGE_MODEL_ID", "stabilityai/sd-turbo"),
            "device": self.device,
            "model_loaded": self.pipeline is not None,
            "load_error": self._load_error,
            "last_used": self._last_used,
        }


def get_local_model_manager() -> LocalImageModelManager:
    """Returns the singleton instance of LocalImageModelManager."""
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = LocalImageModelManager()
    return _manager_instance
