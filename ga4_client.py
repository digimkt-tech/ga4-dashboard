from __future__ import annotations

from datetime import date
from typing import Sequence

import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account

from config import AppConfig


GA4_SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
DEFAULT_GA4_METRICS: tuple[str, ...] = (
    "sessions",
    "engagedSessions",
    "keyEvents",
    "totalRevenue",
)


def _build_client(config: AppConfig) -> BetaAnalyticsDataClient:
    credentials_path = config.effective_ga4_credentials_path
    if credentials_path:
        try:
            credentials = service_account.Credentials.from_service_account_file(
                str(credentials_path),
                scopes=GA4_SCOPES,
            )
            return BetaAnalyticsDataClient(credentials=credentials)
        except ValueError as exc:
            print(f"Warning: Failed to parse {credentials_path} as Service Account JSON. Falling back to OAuth. Error: {exc}")

    if config.google_ads_refresh_token and config.google_ads_client_id and config.google_ads_client_secret:
        from google.oauth2.credentials import Credentials
        credentials = Credentials(
            token=None,
            refresh_token=config.google_ads_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config.google_ads_client_id,
            client_secret=config.google_ads_client_secret,
            scopes=GA4_SCOPES,
        )
        return BetaAnalyticsDataClient(credentials=credentials)

    return BetaAnalyticsDataClient()


def fetch_ga4_campaign_report(
    config: AppConfig,
    property_id: str,
    start_date: date,
    end_date: date,
    metrics: Sequence[str] | None = None,
    page_size: int = 100_000,
) -> pd.DataFrame:
    if not property_id:
        raise ValueError("GA4_PROPERTY_ID is missing.")

    if not config.ga4_ready:
        raise ValueError(
            "GA4 credentials are missing. Use Service Account JSON or User OAuth Refresh Token."
        )

    metric_names = list(metrics or DEFAULT_GA4_METRICS)
    dimension_names = [
        name
        for name in dict.fromkeys(
            [
                "date",
                config.ga4_campaign_id_dimension,
                config.ga4_campaign_dimension,
            ]
        )
        if name
    ]

    client = _build_client(config)
    rows: list[dict[str, object]] = []
    offset = 0

    while True:
        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[
                DateRange(start_date=str(start_date), end_date=str(end_date))
            ],
            dimensions=[Dimension(name=name) for name in dimension_names],
            metrics=[Metric(name=name) for name in metric_names],
            limit=page_size,
            offset=offset,
        )
        response = client.run_report(request)

        if not response.rows:
            break

        for row in response.rows:
            parsed_row: dict[str, object] = {}
            for header, value in zip(response.dimension_headers, row.dimension_values):
                parsed_row[header.name] = value.value
            for header, value in zip(response.metric_headers, row.metric_values):
                parsed_row[header.name] = value.value
            rows.append(parsed_row)

        offset += len(response.rows)
        if offset >= response.row_count:
            break

    standard_columns = [
        "date",
        "ga4_campaign_id",
        "ga4_campaign_name",
        "ga4_sessions",
        "ga4_engaged_sessions",
        "ga4_key_events",
        "ga4_total_revenue",
    ]
    if not rows:
        return pd.DataFrame({
            "date": pd.Series(dtype="datetime64[ns]"),
            "ga4_campaign_id": pd.Series(dtype="object"),
            "ga4_campaign_name": pd.Series(dtype="object"),
            "ga4_sessions": pd.Series(dtype="float64"),
            "ga4_engaged_sessions": pd.Series(dtype="float64"),
            "ga4_key_events": pd.Series(dtype="float64"),
            "ga4_total_revenue": pd.Series(dtype="float64"),
        })

    frame = pd.DataFrame(rows).rename(
        columns={
            config.ga4_campaign_id_dimension: "ga4_campaign_id",
            config.ga4_campaign_dimension: "ga4_campaign_name",
            "sessions": "ga4_sessions",
            "engagedSessions": "ga4_engaged_sessions",
            "keyEvents": "ga4_key_events",
            "totalRevenue": "ga4_total_revenue",
        }
    )

    if "ga4_campaign_id" not in frame.columns:
        frame["ga4_campaign_id"] = ""
    if "ga4_campaign_name" not in frame.columns:
        frame["ga4_campaign_name"] = "(not set)"

    frame["date"] = pd.to_datetime(frame["date"], format="%Y%m%d", errors="coerce")
    frame["ga4_campaign_id"] = (
        frame["ga4_campaign_id"].fillna("").astype(str).str.strip()
    )
    frame["ga4_campaign_name"] = (
        frame["ga4_campaign_name"]
        .fillna("(not set)")
        .astype(str)
        .str.strip()
    )

    for column in [
        "ga4_sessions",
        "ga4_engaged_sessions",
        "ga4_key_events",
        "ga4_total_revenue",
    ]:
        if column not in frame.columns:
            frame[column] = 0.0
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)

    return frame[standard_columns].sort_values(["date", "ga4_campaign_name"])
