from __future__ import annotations

from datetime import date

import pandas as pd
from google.ads.googleads.client import GoogleAdsClient

from config import AppConfig


def _build_client(config: AppConfig) -> GoogleAdsClient:
    if config.google_ads_config_path and config.google_ads_config_path.exists():
        return GoogleAdsClient.load_from_storage(str(config.google_ads_config_path))

    config_dict = config.google_ads_config_dict()
    if config_dict:
        return GoogleAdsClient.load_from_dict(config_dict)

    raise ValueError(
        "Google Ads credentials are incomplete. Provide google-ads.yaml or the "
        "required GOOGLE_ADS_* environment variables."
    )


def fetch_ads_campaign_report(
    config: AppConfig,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    if not config.google_ads_customer_id:
        raise ValueError("GOOGLE_ADS_CUSTOMER_ID is missing.")

    client = _build_client(config)
    google_ads_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            segments.date,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE
            segments.date BETWEEN '{start_date:%Y-%m-%d}' AND '{end_date:%Y-%m-%d}'
            AND campaign.status != 'REMOVED'
        ORDER BY segments.date, campaign.name
    """

    stream = google_ads_service.search_stream(
        customer_id=config.google_ads_customer_id,
        query=query,
    )

    rows: list[dict[str, object]] = []
    for batch in stream:
        for row in batch.results:
            rows.append(
                {
                    "date": row.segments.date,
                    "ads_campaign_id": str(row.campaign.id),
                    "ads_campaign_name": row.campaign.name,
                    "ads_impressions": int(row.metrics.impressions),
                    "ads_clicks": int(row.metrics.clicks),
                    "ads_cost": float(row.metrics.cost_micros) / 1_000_000,
                    "ads_conversions": float(row.metrics.conversions),
                    "ads_conversions_value": float(
                        row.metrics.conversions_value
                    ),
                }
            )

    standard_columns = [
        "date",
        "ads_campaign_id",
        "ads_campaign_name",
        "ads_impressions",
        "ads_clicks",
        "ads_cost",
        "ads_conversions",
        "ads_conversions_value",
    ]
    if not rows:
        return pd.DataFrame({
            "date": pd.Series(dtype="datetime64[ns]"),
            "ads_campaign_id": pd.Series(dtype="object"),
            "ads_campaign_name": pd.Series(dtype="object"),
            "ads_impressions": pd.Series(dtype="float64"),
            "ads_clicks": pd.Series(dtype="float64"),
            "ads_cost": pd.Series(dtype="float64"),
            "ads_conversions": pd.Series(dtype="float64"),
            "ads_conversions_value": pd.Series(dtype="float64"),
        })

    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["ads_campaign_id"] = (
        frame["ads_campaign_id"].fillna("").astype(str).str.strip()
    )
    frame["ads_campaign_name"] = (
        frame["ads_campaign_name"].fillna("(unnamed)").astype(str).str.strip()
    )

    for column in [
        "ads_impressions",
        "ads_clicks",
        "ads_cost",
        "ads_conversions",
        "ads_conversions_value",
    ]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)

    return frame[standard_columns].sort_values(["date", "ads_campaign_name"])
