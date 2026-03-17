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


def _build_skeleton(config: dict, trips_dir: Path, output_dir: Path | None) -> None:
    """Create a skeleton trip.json + empty app HTML so the trip is immediately navigable."""
    from vacationeer.models.trip import Preferences, Trip
    from vacationeer.storage.json_store import save_trip

    slug = config["id"]
    trip_json_path = trips_dir / "trip.json"

    # Build minimal Trip from config
    prefs_data = config.get("preferences", {})
    skeleton = Trip(
        id=slug,
        name=config.get("name", config.get("destination", slug)),
        destination=config["destination"],
        start_date=config["start_date"],
        end_date=config["end_date"],
        travelers=config.get("travelers", 2),
        budget_eur=config.get("budget_eur"),
        preferences=Preferences(**prefs_data) if prefs_data else None,
        attractions=[],
        day_trips=[],
        days=[],
    )
    save_trip(skeleton, trip_json_path)
    log.info("Pipeline [%s]: skeleton trip.json saved", slug)

    # Build empty app HTML (so the trip page is immediately accessible)
    if output_dir:
        try:
            from vacationeer.views.app_shell import generate_app
            from vacationeer.views.overview import render_overview
            from vacationeer.views.timeline import render_timeline

            output_dir.mkdir(parents=True, exist_ok=True)
            dest_slug = skeleton.destination.lower().replace(" ", "-")
            map_filename = f"{dest_slug}-map.html"

            # Placeholder map (no attractions yet — generate_map raises on empty)
            placeholder_map = f"""<!DOCTYPE html>
<html><head>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css"/>
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"></script>
<style>html,body{{width:100%;height:100%;margin:0;padding:0;}}
#map{{position:absolute;top:0;bottom:0;left:0;right:0;}}
.loading-overlay{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
z-index:1000;background:rgba(255,255,255,0.95);padding:20px 32px;border-radius:12px;
box-shadow:0 4px 20px rgba(0,0,0,.15);font-family:system-ui,sans-serif;text-align:center;}}
.loading-overlay .spinner{{width:32px;height:32px;border:3px solid #e0e0e0;
border-top:3px solid #1a2332;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 12px;}}
@keyframes spin{{to{{transform:rotate(360deg);}}}}
</style></head><body>
<div id="map"></div>
<div class="loading-overlay"><div class="spinner"></div>Researching attractions...</div>
<script>var m=L.map('map').setView([39.47,-0.38],13);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png',
{{subdomains:'abcd',maxZoom:20}}).addTo(m);
</script></body></html>"""
            (output_dir / map_filename).write_text(placeholder_map, encoding="utf-8")

            tab_contents = {
                "overview-content": render_overview(skeleton),
                "timeline-content": render_timeline(skeleton),
            }
            generate_app(
                skeleton, map_filename,
                output_dir / f"{dest_slug}-app.html",
                tab_contents=tab_contents,
            )
            log.info("Pipeline [%s]: skeleton app HTML built", slug)
        except Exception as e:
            log.warning("Pipeline [%s]: skeleton HTML build failed (non-fatal): %s", slug, e)


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

    # Create skeleton trip + app HTML immediately (so trip is navigable right away)
    _build_skeleton(config, trips_dir, output_dir)

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
