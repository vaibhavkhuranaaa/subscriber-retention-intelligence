from __future__ import annotations

import csv
import io
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from retention_api.scenario import ScenarioRequest, calculate_scenario, load_curve

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIR = Path(
    os.getenv("RETENTION_PRIVATE_DIR", ROOT.parent / f"{ROOT.name}-ops" / "data/private")
)
WAREHOUSE = Path(os.getenv("RETENTION_WAREHOUSE_PATH", PRIVATE_DIR / "warehouse/retention.duckdb"))
WEB_DIST = Path(os.getenv("RETENTION_WEB_DIST", ROOT / "web/dist"))
MODE = os.getenv("RETENTION_MODE", "private")
RELEASE_ID = os.getenv("RETENTION_RELEASE_ID", "local-m8")
WINDOWS = {"2017-02", "2017-03"}
DIMENSIONS = {"payment_method", "plan_days", "registration_method", "auto_renew"}
TOKEN_PATTERN = re.compile(r"^[0-9a-f]{24}$")
SOURCE_ATTRIBUTION = {
    "provider": "KKBox",
    "collection": "WSDM Churn Prediction Challenge",
    "source_url": "https://www.kaggle.com/competitions/kkbox-churn-prediction-challenge",
    "usage": "Owner-approved public analysis and pseudonymized detailed release; source identifiers excluded.",
}


def serializable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


@contextmanager
def connection() -> Iterator[duckdb.DuckDBPyConnection]:
    if not WAREHOUSE.exists():
        raise HTTPException(
            status_code=503,
            detail="Semantic warehouse unavailable. Run the semantic build.",
        )
    database = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        database.execute("set threads = 1")
        yield database
    finally:
        database.close()


def rows(sql: str, parameters: list[Any] | None = None) -> list[dict[str, Any]]:
    with connection() as database:
        result = database.execute(sql, parameters or [])
        columns = [column[0] for column in result.description]
        return [
            {column: serializable(value) for column, value in zip(columns, row, strict=True)}
            for row in result.fetchall()
        ]


def envelope(data: Any, label_window: str | None = None, mode: str | None = None) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {
            "as_of": label_window or "2017-03",
            "release_id": RELEASE_ID,
            "mode": mode or MODE,
            "metric_version": "m8.1",
            "filters": {"label_window": label_window} if label_window else {},
        },
    }


def validate_window(label_window: str) -> str:
    if label_window not in WINDOWS:
        raise HTTPException(status_code=422, detail="label_window must be 2017-02 or 2017-03")
    return label_window


def create_app(mode: Literal["private", "public"] | None = None) -> FastAPI:
    active_mode = mode or MODE
    app = FastAPI(title="Subscriber Retention Intelligence", version="1.0.0")

    def response(data: Any, label_window: str | None = None) -> dict[str, Any]:
        return envelope(data, label_window, active_mode)

    @app.get("/api/v1/status")
    def status() -> dict[str, Any]:
        available = rows(
            "select label_window, history_cutoff, eligible_subscribers from public_retention_overview order by label_window"
        )
        return response(
            {
                "status": "ready",
                "product": "Subscriber Retention Intelligence",
                "available_windows": available,
                "freshness": "Historical source through 2017-03-31",
                "privacy_boundary": "private drill-down"
                if active_mode == "private"
                else "aggregate only",
                "attribution": SOURCE_ATTRIBUTION,
            }
        )

    @app.get("/api/v1/overview")
    def overview(label_window: str = Query("2017-03")) -> dict[str, Any]:
        label_window = validate_window(label_window)
        data = rows(
            "select * from public_retention_overview where label_window = ?",
            [label_window],
        )
        if not data:
            raise HTTPException(status_code=404, detail="No overview exists for this window")
        return response(data[0], label_window)

    @app.get("/api/v1/cohorts")
    def cohorts(
        label_window: str = Query("2017-03"),
        limit: int = Query(48, ge=1, le=240),
    ) -> dict[str, Any]:
        label_window = validate_window(label_window)
        relation = "mart_renewal_cohort" if active_mode == "private" else "public_renewal_cohort"
        data = rows(
            f"""
            select * from {relation}
            where label_window = ?
              and registration_cohort_month is not null
              and registration_cohort_month <= case label_window
                  when '2017-02' then date '2017-01-01'
                  when '2017-03' then date '2017-02-01'
              end
            order by registration_cohort_month desc limit ?
            """,
            [label_window, limit],
        )
        return response(data, label_window)

    @app.get("/api/v1/segments")
    def segments(
        label_window: str = Query("2017-03"),
        dimension: str = Query("engagement"),
        limit: int = Query(16, ge=1, le=50),
    ) -> dict[str, Any]:
        label_window = validate_window(label_window)
        if dimension == "engagement":
            relation = (
                "mart_engagement_segment"
                if active_mode == "private"
                else "public_engagement_segment"
            )
            data = rows(
                f"select * from {relation} where label_window = ? order by observed_churn_rate desc",
                [label_window],
            )
        elif dimension in DIMENSIONS:
            relation = (
                "mart_subscription_segment"
                if active_mode == "private"
                else "public_subscription_segment"
            )
            data = rows(
                f"""
                select * from {relation}
                where label_window = ? and dimension = ?
                order by eligible_subscribers desc limit ?
                """,
                [label_window, dimension, limit],
            )
        else:
            raise HTTPException(status_code=422, detail="Unsupported segment dimension")
        return response(data, label_window)

    @app.get("/api/v1/definitions")
    def definitions() -> dict[str, Any]:
        return response(rows("select * from public_metric_definition order by metric_id"))

    @app.get("/api/v1/export/{resource}.csv")
    def export(
        resource: Literal["overview", "cohorts", "segments"],
        label_window: str = Query("2017-03"),
    ) -> Response:
        label_window = validate_window(label_window)
        queries = {
            "overview": (
                "select * from public_retention_overview where label_window = ?",
                [label_window],
            ),
            "cohorts": (
                """
                select * from public_renewal_cohort
                where label_window = ?
                  and registration_cohort_month <= case label_window
                      when '2017-02' then date '2017-01-01'
                      when '2017-03' then date '2017-02-01'
                  end
                order by registration_cohort_month
                """,
                [label_window],
            ),
            "segments": (
                "select * from public_subscription_segment where label_window = ? order by dimension, eligible_subscribers desc",
                [label_window],
            ),
        }
        sql, parameters = queries[resource]
        data = rows(sql, parameters)
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return Response(
            output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="retention-{resource}-{label_window}.csv"'
            },
        )

    if active_mode == "private":

        @app.post("/api/v1/scenario")
        def scenario(request: ScenarioRequest) -> dict[str, Any]:
            try:
                data = calculate_scenario(load_curve(), **request.model_dump())
            except FileNotFoundError as reason:
                raise HTTPException(status_code=503, detail=str(reason)) from reason
            except ValueError as reason:
                raise HTTPException(status_code=422, detail=str(reason)) from reason
            return response(data, "2017-03")

        @app.get("/api/v1/subscribers")
        def subscribers(
            label_window: str = Query("2017-03"),
            engagement_segment: str | None = Query(None),
            outcome: Literal["all", "renewed", "churned"] = Query("all"),
            limit: int = Query(20, ge=1, le=50),
        ) -> dict[str, Any]:
            label_window = validate_window(label_window)
            conditions = ["label_window = ?"]
            parameters: list[Any] = [label_window]
            if engagement_segment:
                conditions.append("engagement_segment = ?")
                parameters.append(engagement_segment)
            if outcome != "all":
                conditions.append("is_churn = ?")
                parameters.append(1 if outcome == "churned" else 0)
            parameters.append(limit)
            data = rows(
                f"""
                select
                    hex(subscriber_token) as subscriber_token,
                    label_window,
                    is_churn,
                    is_active_at_cutoff,
                    effective_expiration_date,
                    engagement_segment,
                    gross_receipts_90d,
                    listening_active_days_30d,
                    latest_payment_plan_days,
                    latest_is_auto_renew
                from mart_private_review_population
                where {" and ".join(conditions)}
                order by gross_receipts_90d desc, subscriber_token
                limit ?
                """,
                parameters,
            )
            return response(data, label_window)

        @app.get("/api/v1/subscribers/{subscriber_token}")
        def subscriber(
            subscriber_token: str, label_window: str = Query("2017-03")
        ) -> dict[str, Any]:
            label_window = validate_window(label_window)
            token = subscriber_token.lower()
            if not TOKEN_PATTERN.fullmatch(token):
                raise HTTPException(
                    status_code=422,
                    detail="subscriber_token must be 24 hexadecimal characters",
                )
            profile = rows(
                "select * exclude (subscriber_token), hex(subscriber_token) as subscriber_token from mart_private_review_population where subscriber_token = unhex(?) and label_window = ?",
                [token, label_window],
            )
            if not profile:
                raise HTTPException(
                    status_code=404, detail="Subscriber not found in this label window"
                )
            transactions = rows(
                """
                select transaction_date, membership_expire_date, payment_plan_days,
                       actual_amount_paid, is_auto_renew, is_cancel
                from mart_private_review_transaction
                where subscriber_token = unhex(?) and label_window = ?
                order by transaction_date desc, same_day_sequence desc limit 24
                """,
                [token, label_window],
            )
            listening = rows(
                """
                select activity_month, active_days, listening_seconds, unique_track_count
                from mart_private_review_listening_monthly
                where subscriber_token = unhex(?) and label_window = ?
                order by activity_month
                """,
                [token, label_window],
            )
            return response(
                {
                    "profile": profile[0],
                    "transactions": transactions,
                    "listening_monthly": listening,
                },
                label_window,
            )

    dist = WEB_DIST
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app


app = create_app()
