from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TypeVar

import anyio

from app.core.config import settings

T = TypeVar("T")

_face_job_semaphore = asyncio.Semaphore(max(1, settings.face_processing_concurrency))


async def run_face_job(job: Callable[[], T]) -> T:
    async with _face_job_semaphore:
        return await anyio.to_thread.run_sync(job)
