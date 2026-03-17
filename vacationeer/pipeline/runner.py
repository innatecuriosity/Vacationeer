"""Background pipeline runner for trip creation.

Runs research + conversion in a thread, tracks progress via a shared state dict.
"""
from __future__ import annotations

import json
import logging
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

log = logging.getLogger("vacationeer.pipeline")


@dataclass
class PipelineJob:
    slug: str
    config: dict
    status: str = "queued"  # queued, researching, converting, building, done, error
    step: str = ""
    error: str | None = None
    started_at: str = ""
    finished_at: str | None = None
    attractions_count: int = 0
    day_trips_count: int = 0

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "status": self.status,
            "step": self.step,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "attractions_count": self.attractions_count,
            "day_trips_count": self.day_trips_count,
        }


# Global job registry — keyed by slug
_jobs: dict[str, PipelineJob] = {}
_lock = threading.Lock()


def get_job(slug: str) -> PipelineJob | None:
    with _lock:
        return _jobs.get(slug)


def list_jobs() -> list[dict]:
    with _lock:
        return [j.to_dict() for j in _jobs.values()]


def _run_pipeline(job: PipelineJob, project_root: Path, light: bool, output_dir: Path | None) -> None:
    """Execute the full pipeline: research → convert → build."""
    from vacationeer.pipeline.ai_provider import get_provider
    from vacationeer.pipeline.converter import convert_to_trip
    from vacationeer.pipeline.research import generate_research

    config = job.config
    slug = config["id"]
    data_dir = project_root / "data" / slug
    trips_dir = project_root / "trips" / slug
    trip_json_path = trips_dir / "trip.json"

    try:
        provider = get_provider()
        log.info("Pipeline [%s]: using provider %s", slug, provider.name)

        # Step 1: Research
        job.status = "researching"
        job.step = f"Generating research with {provider.name}..."
        log.info("Pipeline [%s]: starting research", slug)

        # generate_research uses click.echo — suppress by importing without CLI
        from vacationeer.pipeline.research import (
            build_research_prompt,
            _parse_files_from_response,
            RESEARCH_SYSTEM,
        )
        from vacationeer.pipeline.templates import RESEARCH_SYSTEM as SYS

        prompt = build_research_prompt(config, light=light)
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "research-instructions.md").write_text(prompt, encoding="utf-8")

        response = provider.complete(prompt, system=SYS)
        parsed = _parse_files_from_response(response)

        for filename in ["attractions-and-activities.md", "day-trips.md", "good-to-know.md"]:
            content = parsed.get(filename, "")
            if content:
                (data_dir / filename).write_text(content, encoding="utf-8")
                log.info("Pipeline [%s]: saved %s", slug, filename)

        (data_dir / "research-raw-response.md").write_text(response, encoding="utf-8")
        job.step = "Research complete"

        # Step 2: Convert
        job.status = "converting"
        job.step = "Converting research to trip.json..."
        log.info("Pipeline [%s]: starting conversion", slug)

        from vacationeer.pipeline.converter import (
            build_conversion_prompt,
            _extract_json,
            validate_and_save,
        )
        from vacationeer.pipeline.templates import CONVERSION_SYSTEM

        conv_prompt = build_conversion_prompt(config, data_dir)
        (data_dir / "conversion-prompt.md").write_text(conv_prompt, encoding="utf-8")

        conv_response = provider.complete(conv_prompt, system=CONVERSION_SYSTEM)
        json_text = _extract_json(conv_response)
        (data_dir / "conversion-raw-response.json").write_text(json_text, encoding="utf-8")

        trip = validate_and_save(json_text, trip_json_path)
        job.attractions_count = len(trip.attractions)
        job.day_trips_count = len(trip.day_trips)
        job.step = f"Converted: {len(trip.attractions)} attractions, {len(trip.day_trips)} day trips"
        log.info("Pipeline [%s]: conversion done — %d attractions, %d day trips",
                 slug, len(trip.attractions), len(trip.day_trips))

        # Step 3: Build HTML
        if output_dir:
            job.status = "building"
            job.step = "Building app HTML..."
            log.info("Pipeline [%s]: building HTML", slug)

            from vacationeer.maps.generator import generate_map
            from vacationeer.storage.json_store import load_trip
            from vacationeer.views.app_shell import generate_app
            from vacationeer.views.overview import render_overview
            from vacationeer.views.timeline import render_timeline

            trip = load_trip(trip_json_path)
            dest_slug = trip.destination.lower().replace(" ", "-")
            map_filename = f"{dest_slug}-map.html"
            generate_map(trip, output_dir / map_filename)
            tab_contents = {
                "overview-content": render_overview(trip),
                "timeline-content": render_timeline(trip),
            }
            generate_app(trip, map_filename, output_dir / f"{dest_slug}-app.html", tab_contents=tab_contents)
            log.info("Pipeline [%s]: HTML built", slug)

        # Done
        job.status = "done"
        job.step = "Trip ready!"
        job.finished_at = datetime.now().isoformat()
        log.info("Pipeline [%s]: complete", slug)

    except Exception as e:
        job.status = "error"
        job.error = str(e)
        job.step = f"Failed: {e}"
        job.finished_at = datetime.now().isoformat()
        log.error("Pipeline [%s]: error — %s\n%s", slug, e, traceback.format_exc())


def start_pipeline(
    config: dict,
    project_root: Path,
    *,
    light: bool = True,
    output_dir: Path | None = None,
) -> PipelineJob:
    """Start the pipeline in a background thread. Returns the job."""
    slug = config["id"]

    # Save config
    trips_dir = project_root / "trips" / slug
    trips_dir.mkdir(parents=True, exist_ok=True)
    config_path = trips_dir / "trip-config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    job = PipelineJob(
        slug=slug,
        config=config,
        started_at=datetime.now().isoformat(),
    )

    with _lock:
        _jobs[slug] = job

    thread = threading.Thread(
        target=_run_pipeline,
        args=(job, project_root, light, output_dir),
        daemon=True,
        name=f"pipeline-{slug}",
    )
    thread.start()
    return job
