"""Madkhal HTTP API (FastAPI), versioned under /v1.

Advisory only. Read only. Errors are application/problem+json (RFC 9457). Inputs are bounded,
responses never contain server file paths, and identifiers come from an inputs hash.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from madkhal import __version__
from madkhal.contract import Advisory, BloomBelief, Dataset, Scenario, Site
from madkhal.core.errors import InputError, MadkhalError, UnknownSiteError
from madkhal.core.jsonio import inputs_hash

from . import service

PROBLEM = "application/problem+json"
MAX_BODY_BYTES = 64 * 1024
log = logging.getLogger("madkhal.api")


def problem(status: int, title: str, detail: str, type_: str = "about:blank") -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"type": type_, "title": title, "status": status, "detail": detail},
        media_type=PROBLEM,
    )


class BodyLimit(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        length = request.headers.get("content-length")
        if length is not None and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return problem(
                413, "Request too large", f"Request bodies are limited to {MAX_BODY_BYTES} bytes."
            )
        return await call_next(request)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Madkhal API",
        version=__version__,
        description=(
            "Advisory decision support for a hypothetical SWRO intake. Evidence: real satellite "
            "history from the Nadhir hindcast. Plant, drone and consequences: hypothetical, "
            "synthetic parameters. Read only; controls nothing."
        ),
        openapi_url="/v1/openapi.json",
        docs_url="/v1/docs",
        redoc_url=None,
    )
    app.add_middleware(BodyLimit)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"],
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )

    @app.exception_handler(UnknownSiteError)
    async def _unknown(_: Request, exc: UnknownSiteError) -> JSONResponse:
        return problem(404, "Not found", str(exc))

    @app.exception_handler(InputError)
    async def _input(_: Request, exc: InputError) -> JSONResponse:
        return problem(422, "Invalid input", str(exc))

    @app.exception_handler(service.NotAvailable)
    async def _not_available(_: Request, exc: service.NotAvailable) -> JSONResponse:
        return problem(503, "Not available", str(exc))

    @app.exception_handler(MadkhalError)
    async def _madkhal(_: Request, exc: MadkhalError) -> JSONResponse:
        log.error("madkhal error: %s", exc)
        return problem(500, "Internal error", "The evidence base could not be read.")

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        parts = []
        for e in exc.errors():
            loc = ".".join(str(x) for x in e.get("loc", ()) if x not in ("query", "path", "body"))
            parts.append(f"{loc}: {e.get('msg', 'invalid')}")
        return problem(422, "Invalid input", "; ".join(parts) or "invalid request")

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException) -> JSONResponse:
        return problem(exc.status_code, "Error", str(exc.detail))

    @app.exception_handler(404)
    async def _not_found(_: Request, __: Exception) -> JSONResponse:
        return problem(404, "Not found", "No such resource.")

    @app.exception_handler(Exception)
    async def _any(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error")
        return problem(500, "Internal error", "Unexpected error.")

    # ------------------------------------------------------------------ routes
    @app.get("/v1/health", tags=["meta"])
    def health() -> dict[str, Any]:
        return service.health()

    @app.get("/v1/sites", response_model=list[Site], tags=["evidence"])
    def sites(dataset: Dataset = Dataset.olci_v1) -> list[Site]:
        return service.sites(dataset)

    @app.get("/v1/evidence/{site}", tags=["evidence"])
    def evidence(site: str, radius: int = Query(50, ge=25, le=100)) -> dict[str, Any]:
        return service.evidence(site, radius)

    @app.get("/v1/track-record", tags=["evidence"])
    def track_record() -> dict[str, Any]:
        return service.track_record()

    @app.get("/v1/belief/{site}", response_model=BloomBelief, tags=["belief"])
    def belief(
        response: Response,
        site: str,
        date: str | None = Query(
            None, max_length=10, description="ISO date; default the last evidence day."
        ),
        horizon: int = Query(3, description="Highlighted horizon in days: 1, 3 or 7."),
        draws: int = Query(service.DEFAULT_DRAWS, ge=50, le=service.MAX_DRAWS),
        seed: int = Query(service.DEFAULT_SEED, ge=0, le=2**31 - 1),
    ) -> BloomBelief:
        if horizon not in (1, 3, 7):
            raise InputError("horizon must be 1, 3 or 7")
        out = service.belief(site, date, draws, seed)
        response.headers["ETag"] = (
            '"'
            + inputs_hash({"site": site, "date": str(out.date), "draws": draws, "seed": seed})
            + '"'
        )
        return out

    @app.get("/v1/belief/{site}/series", tags=["belief"])
    def belief_series(
        site: str,
        start: str | None = Query(None, max_length=10),
        end: str | None = Query(None, max_length=10),
    ) -> dict[str, Any]:
        return service.belief_series(site, start, end)

    @app.get("/v1/advisory/{site}", response_model=Advisory, tags=["decision"])
    def advisory(
        site: str,
        date: str | None = Query(
            None, max_length=10, description="ISO date; default the last evidence day."
        ),
        profile: str = Query(service.PROFILE_ID, max_length=64),
        fouling_index: float = Query(0.2, ge=0.0, le=1.5),
        storage_hours: float = Query(24.0, ge=0.0, le=72.0),
    ) -> Advisory:
        return service.advisory(site, date, profile, fouling_index, storage_hours)

    @app.get("/v1/timeline/{site}", tags=["decision"])
    def timeline(
        site: str,
        start: str | None = Query(None, max_length=10),
        end: str | None = Query(None, max_length=10),
    ) -> dict[str, Any]:
        return service.timeline(site, start, end)

    @app.post("/v1/scenario/advise", tags=["decision"])
    def scenario(sc: Scenario) -> dict[str, Any]:
        return service.scenario(sc)

    @app.get("/v1/plant/profile", tags=["plant"])
    def plant_profile() -> dict[str, Any]:
        return service.plant_profile()

    @app.get("/v1/plant/sensitivity", tags=["plant"])
    def plant_sensitivity() -> dict[str, Any]:
        return service.plant_sensitivity()

    @app.get("/v1/policies/results", tags=["lab"])
    def policies_results() -> dict[str, Any]:
        return service.policies_results()

    @app.get("/v1/replay/{site}", tags=["lab"])
    def replay(site: str) -> dict[str, Any]:
        return service.replay(site)

    @app.get("/v1/method", tags=["meta"])
    def method() -> dict[str, Any]:
        return service.method()

    @app.get("/v1/claims", tags=["meta"])
    def claims() -> dict[str, Any]:
        return service.claims()

    @app.get("/v1/provenance", tags=["meta"])
    def provenance() -> dict[str, Any]:
        return service.provenance()

    @app.get("/v1/missions/{site}", tags=["tasking"])
    def missions(
        site: str,
        date: str | None = Query(None, max_length=10),
        radius_m: float = Query(3000.0, gt=0, le=20000),
        width_m: float = Query(1600.0, ge=100, le=20000),
        spacing_m: float = Query(800.0, ge=100, le=5000),
        altitude_m: float = Query(90.0, ge=60, le=120),
        endurance_min: float = Query(25.0, gt=0, le=180),
        sortie_cost: float = Query(1000.0, ge=0, le=1e7),
    ) -> dict[str, Any]:
        return service.missions(
            site, date, radius_m, width_m, spacing_m, altitude_m, endurance_min, sortie_cost
        )

    return app


app = create_app()
