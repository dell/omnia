"""
Local repository routes for Config Editor Module

Provides API endpoints for local repository configuration generation.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from typing import Dict, Any, Optional
from pathlib import Path

from ....services.local_repo_generator_service import LocalRepoGeneratorService
from ....services.job_store import JobStore, TooManyConcurrentJobsError
from ....api.v1.dependencies import get_local_repo_generator_service

logger = logging.getLogger(__name__)
router = APIRouter()


def run_local_repo_generation(
    job_id: str,
    data: Dict[str, Any],
    output_dir: Optional[Path],
    local_repo_generator_service: LocalRepoGeneratorService,
    job_store: JobStore,
) -> None:
    """Run local repo generation in background.

    Args:
        job_id: Job identifier
        data: Local repo management data
        output_dir: Optional output directory Path
        local_repo_generator_service: Local repo generator service instance
        job_store: Job store instance for tracking state
    """
    try:
        job_store.update_job(job_id, status="in_progress", progress=10)

        result = local_repo_generator_service.generate_local_repo_configs(
            job_id=job_id,
            update_job=job_store.update_job,
            data=data,
            output_dir=output_dir,
        )

        logger.info("Local repo config generation completed for job %s", job_id)
        job_store.update_job(job_id, progress=100, status="completed", result=result)

    except Exception as e:
        logger.exception("Local repo config generation failed for job %s", job_id)
        job_store.update_job(job_id, status="failed", error=str(e), result={"error": str(e)})


@router.post("/generate")
async def generate_local_repo(
    data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    request: Request,
    local_repo_generator_service: LocalRepoGeneratorService = Depends(get_local_repo_generator_service),
) -> Dict[str, str]:
    """Trigger local repository configuration generation.

    Args:
        data: Local repo management data with rhel and ubuntu sections
        background_tasks: FastAPI background tasks
        request: FastAPI request object
        local_repo_generator_service: Local repo generator service instance

    Returns:
        Dictionary with job_id
    """
    job_store = request.app.state.job_store

    try:
        job_id = job_store.create_job()
    except TooManyConcurrentJobsError:
        raise HTTPException(429, "Too many generation jobs in progress. Please wait.")

    output_dir = data.get("output_dir", None)
    output_path = Path(output_dir).expanduser().resolve() if output_dir else None

    generation_data = {k: v for k, v in data.items() if k != "output_dir"}

    background_tasks.add_task(
        run_local_repo_generation,
        job_id,
        generation_data,
        output_path,
        local_repo_generator_service,
        job_store,
    )

    logger.info("Started local repo config generation job %s", job_id)
    return {"job_id": job_id, "status": "pending"}
