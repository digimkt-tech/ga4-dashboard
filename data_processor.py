from __future__ import annotations

import math
import re
from datetime import date
from random import Random

import pandas as pd


GA4_COLUMNS = [
    "date",
    "ga4_campaign_id",
    "ga4_campaign_name",
    "ga4_sessions",
    "ga4_engaged_sessions",
    "ga4_key_events",
    "ga4_total_revenue",
]

ADS_COLUMNS = [
    "date",
    "ads_campaign_id",
    "ads_campaign_name",
    "ads_impressions",
    "ads_clicks",
    "ads_cost",
    "ads_conversions",
    "ads_conversions_value",
]

MERGED_NUMERIC_COLUMNS = [
    "ga4_sessions",
    "ga4_engaged_sessions",
    "ga4_key_events",
    "ga4_total_revenue",
    "ads_impressions",
    "ads_clicks",
    "ads_cost",
    "ads_conversions",
    "ads_conversions_value",
]

GA4_NUMERIC_COLUMNS = [
    "ga4_sessions",
    "ga4_engaged_sessions",
    "ga4_key_events",
    "ga4_total_revenue",
]

ADS_NUMERIC_COLUMNS = [
    "ads_impressions",
    "ads_clicks",
    "ads_cost",
    "ads_conversions",
    "ads_conversions_value",
]


def _coerce_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.normalize()


def _coerce_text(series: pd.Series, fallback: str = "") -> pd.Series:
    return series.fillna(fallback).astype(str).str.strip()


def _coerce_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _safe_ratio(numerator: pd.Series | float, denominator: pd.Series | float):
    if isinstance(numerator, pd.Series):
        return numerator.div(
            denominator.where(denominator != 0)  # type: ignore[union-attr]
        ).fillna(0.0)

    if denominator == 0:
        return 0.0

    return float(numerator) / float(denominator)


def normalize_campaign_name(value: object) -> str:
    if value is None or pd.isna(value):
        return ""

    normalized = re.sub(r"\s+", " ", str(value).strip()).lower()
    return normalized


def clean_ga4_data(frame: pd.DataFrame | None) -> pd.DataFrame:
    working = frame.copy() if frame is not None else pd.DataFrame()
    for column in GA4_COLUMNS:
        if column not in working.columns:
            working[column] = 0.0 if column in GA4_NUMERIC_COLUMNS else ""

    working["date"] = _coerce_datetime(working["date"])
    working["ga4_campaign_id"] = _coerce_text(working["ga4_campaign_id"])
    working["ga4_campaign_name"] = _coerce_text(
        working["ga4_campaign_name"], fallback="(not set)"
    )

    for column in GA4_NUMERIC_COLUMNS:
        working[column] = _coerce_number(working[column])

    return working[GA4_COLUMNS]


def clean_ads_data(frame: pd.DataFrame | None) -> pd.DataFrame:
    working = frame.copy() if frame is not None else pd.DataFrame()
    for column in ADS_COLUMNS:
        if column not in working.columns:
            working[column] = 0.0 if column in ADS_NUMERIC_COLUMNS else ""

    working["date"] = _coerce_datetime(working["date"])
    working["ads_campaign_id"] = _coerce_text(working["ads_campaign_id"])
    working["ads_campaign_name"] = _coerce_text(
        working["ads_campaign_name"], fallback="(unnamed)"
    )

    for column in ADS_NUMERIC_COLUMNS:
        working[column] = _coerce_number(working[column])

    return working[ADS_COLUMNS]


def merge_ga4_and_ads(
    ga4_frame: pd.DataFrame | None,
    ads_frame: pd.DataFrame | None,
) -> pd.DataFrame:
    ga4 = clean_ga4_data(ga4_frame)
    ads = clean_ads_data(ads_frame)

    ga4["merge_key"] = ga4["ga4_campaign_id"].where(
        ga4["ga4_campaign_id"] != "",
        "name::" + ga4["ga4_campaign_name"].map(normalize_campaign_name),
    )
    ads["merge_key"] = ads["ads_campaign_id"].where(
        ads["ads_campaign_id"] != "",
        "name::" + ads["ads_campaign_name"].map(normalize_campaign_name),
    )

    merged = ga4.merge(
        ads,
        on=["date", "merge_key"],
        how="outer",
    )

    merged["ga4_campaign_id"] = _coerce_text(merged["ga4_campaign_id"])
    merged["ads_campaign_id"] = _coerce_text(merged["ads_campaign_id"])
    merged["ga4_campaign_name"] = _coerce_text(
        merged["ga4_campaign_name"], fallback="(not set)"
    )
    merged["ads_campaign_name"] = _coerce_text(
        merged["ads_campaign_name"], fallback="(unnamed)"
    )

    merged["campaign_id"] = merged["ads_campaign_id"].where(
        merged["ads_campaign_id"] != "",
        merged["ga4_campaign_id"],
    )
    merged["campaign_name"] = merged["ads_campaign_name"].where(
        merged["ads_campaign_name"] != "(unnamed)",
        merged["ga4_campaign_name"],
    )

    for column in MERGED_NUMERIC_COLUMNS:
        merged[column] = _coerce_number(merged[column])

    merged["ads_ctr"] = _safe_ratio(
        merged["ads_clicks"],
        merged["ads_impressions"],
    )
    merged["ads_cpc"] = _safe_ratio(merged["ads_cost"], merged["ads_clicks"])
    merged["ads_cpa"] = _safe_ratio(
        merged["ads_cost"],
        merged["ads_conversions"],
    )
    merged["ads_roas"] = _safe_ratio(
        merged["ads_conversions_value"],
        merged["ads_cost"],
    )
    merged["ga4_engagement_rate"] = _safe_ratio(
        merged["ga4_engaged_sessions"],
        merged["ga4_sessions"],
    )
    merged["ga4_key_event_rate"] = _safe_ratio(
        merged["ga4_key_events"],
        merged["ga4_sessions"],
    )
    merged["ga4_revenue_per_session"] = _safe_ratio(
        merged["ga4_total_revenue"],
        merged["ga4_sessions"],
    )
    merged["session_to_click_ratio"] = _safe_ratio(
        merged["ga4_sessions"],
        merged["ads_clicks"],
    )
    merged["conversion_gap"] = (
        merged["ga4_key_events"] - merged["ads_conversions"]
    )

    ordered_columns = [
        "date",
        "campaign_id",
        "campaign_name",
        "ga4_campaign_id",
        "ga4_campaign_name",
        "ads_campaign_id",
        "ads_campaign_name",
        "ga4_sessions",
        "ga4_engaged_sessions",
        "ga4_key_events",
        "ga4_total_revenue",
        "ads_impressions",
        "ads_clicks",
        "ads_cost",
        "ads_conversions",
        "ads_conversions_value",
        "ads_ctr",
        "ads_cpc",
        "ads_cpa",
        "ads_roas",
        "ga4_engagement_rate",
        "ga4_key_event_rate",
        "ga4_revenue_per_session",
        "session_to_click_ratio",
        "conversion_gap",
    ]

    return merged[ordered_columns].sort_values(
        ["date", "campaign_name"],
        ascending=[True, True],
    )


def summarize_dashboard(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty:
        return {
            "campaign_count": 0.0,
            "ads_impressions": 0.0,
            "ads_clicks": 0.0,
            "ads_cost": 0.0,
            "ads_conversions": 0.0,
            "ads_conversions_value": 0.0,
            "ga4_sessions": 0.0,
            "ga4_key_events": 0.0,
            "ga4_total_revenue": 0.0,
            "ads_roas": 0.0,
            "ads_cpa": 0.0,
            "session_to_click_ratio": 0.0,
        }

    totals = {
        "campaign_count": float(frame["campaign_name"].nunique()),
        "ads_impressions": float(frame["ads_impressions"].sum()),
        "ads_clicks": float(frame["ads_clicks"].sum()),
        "ads_cost": float(frame["ads_cost"].sum()),
        "ads_conversions": float(frame["ads_conversions"].sum()),
        "ads_conversions_value": float(frame["ads_conversions_value"].sum()),
        "ga4_sessions": float(frame["ga4_sessions"].sum()),
        "ga4_key_events": float(frame["ga4_key_events"].sum()),
        "ga4_total_revenue": float(frame["ga4_total_revenue"].sum()),
    }
    totals["ads_roas"] = _safe_ratio(
        totals["ads_conversions_value"],
        totals["ads_cost"],
    )
    totals["ads_cpa"] = _safe_ratio(
        totals["ads_cost"],
        totals["ads_conversions"],
    )
    totals["session_to_click_ratio"] = _safe_ratio(
        totals["ga4_sessions"],
        totals["ads_clicks"],
    )
    return totals


def build_daily_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame({
            "date": pd.Series(dtype="datetime64[ns]"),
            "ads_impressions": pd.Series(dtype="float64"),
            "ads_clicks": pd.Series(dtype="float64"),
            "ads_cost": pd.Series(dtype="float64"),
            "ads_conversions": pd.Series(dtype="float64"),
            "ads_conversions_value": pd.Series(dtype="float64"),
            "ga4_sessions": pd.Series(dtype="float64"),
            "ga4_key_events": pd.Series(dtype="float64"),
            "ga4_total_revenue": pd.Series(dtype="float64"),
            "ads_roas": pd.Series(dtype="float64"),
            "session_to_click_ratio": pd.Series(dtype="float64"),
        })

    daily = (
        frame.groupby("date", as_index=False)[
            [
                "ads_impressions",
                "ads_clicks",
                "ads_cost",
                "ads_conversions",
                "ads_conversions_value",
                "ga4_sessions",
                "ga4_key_events",
                "ga4_total_revenue",
            ]
        ]
        .sum()
        .sort_values("date")
    )
    daily["ads_roas"] = _safe_ratio(
        daily["ads_conversions_value"],
        daily["ads_cost"],
    )
    daily["session_to_click_ratio"] = _safe_ratio(
        daily["ga4_sessions"],
        daily["ads_clicks"],
    )
    return daily


def build_campaign_summary(
    frame: pd.DataFrame,
    top_n: int = 10,
    sort_by: str = "ads_cost",
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame({
            "campaign_id": pd.Series(dtype="object"),
            "campaign_name": pd.Series(dtype="object"),
            "ads_impressions": pd.Series(dtype="float64"),
            "ads_clicks": pd.Series(dtype="float64"),
            "ads_cost": pd.Series(dtype="float64"),
            "ads_conversions": pd.Series(dtype="float64"),
            "ads_conversions_value": pd.Series(dtype="float64"),
            "ga4_sessions": pd.Series(dtype="float64"),
            "ga4_key_events": pd.Series(dtype="float64"),
            "ga4_total_revenue": pd.Series(dtype="float64"),
            "ads_roas": pd.Series(dtype="float64"),
            "ads_cpa": pd.Series(dtype="float64"),
            "session_to_click_ratio": pd.Series(dtype="float64"),
        })

    campaign = (
        frame.groupby(["campaign_id", "campaign_name"], as_index=False)[
            [
                "ads_impressions",
                "ads_clicks",
                "ads_cost",
                "ads_conversions",
                "ads_conversions_value",
                "ga4_sessions",
                "ga4_key_events",
                "ga4_total_revenue",
            ]
        ]
        .sum()
    )

    campaign["ads_roas"] = _safe_ratio(
        campaign["ads_conversions_value"],
        campaign["ads_cost"],
    )
    campaign["ads_cpa"] = _safe_ratio(
        campaign["ads_cost"],
        campaign["ads_conversions"],
    )
    campaign["session_to_click_ratio"] = _safe_ratio(
        campaign["ga4_sessions"],
        campaign["ads_clicks"],
    )

    selected_sort = sort_by if sort_by in campaign.columns else "ads_cost"
    campaign = campaign.sort_values(selected_sort, ascending=False)
    return campaign.head(top_n)


def build_demo_data(
    start_date: date,
    end_date: date,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = Random(42)
    date_index = pd.date_range(start=start_date, end=end_date, freq="D")
    campaigns = [
        ("1001", "Brand Search", 125, 1.10, 0.10, 80.0),
        ("1002", "Generic Search", 140, 1.45, 0.07, 65.0),
        ("1003", "Performance Max", 180, 1.20, 0.06, 110.0),
        ("1004", "Remarketing", 95, 0.95, 0.09, 75.0),
    ]

    ga4_rows: list[dict[str, object]] = []
    ads_rows: list[dict[str, object]] = []

    for day_index, current_date in enumerate(date_index):
        for campaign_index, (
            campaign_id,
            campaign_name,
            base_clicks,
            base_cpc,
            base_conversion_rate,
            base_order_value,
        ) in enumerate(campaigns):
            wave = 1.0 + 0.18 * math.sin((day_index + campaign_index * 2) / 4)
            clicks = max(
                12,
                int(base_clicks * wave + rng.randint(-10, 10)),
            )
            impressions = max(
                clicks * 7,
                int(clicks * (7.5 + campaign_index * 1.3) + rng.randint(25, 140)),
            )
            cost = round(
                clicks * base_cpc * rng.uniform(0.92, 1.10),
                2,
            )
            conversions = round(
                clicks * base_conversion_rate * rng.uniform(0.82, 1.16),
                2,
            )
            conversions_value = round(
                conversions * base_order_value * rng.uniform(0.95, 1.20),
                2,
            )
            sessions = max(
                8,
                int(clicks * rng.uniform(0.74, 0.94)),
            )
            engaged_sessions = max(
                5,
                int(sessions * rng.uniform(0.58, 0.84)),
            )
            key_events = round(
                conversions * rng.uniform(0.92, 1.15),
                2,
            )
            total_revenue = round(
                conversions_value * rng.uniform(0.84, 1.08),
                2,
            )

            ads_rows.append(
                {
                    "date": current_date,
                    "ads_campaign_id": campaign_id,
                    "ads_campaign_name": campaign_name,
                    "ads_impressions": impressions,
                    "ads_clicks": clicks,
                    "ads_cost": cost,
                    "ads_conversions": conversions,
                    "ads_conversions_value": conversions_value,
                }
            )
            ga4_rows.append(
                {
                    "date": current_date,
                    "ga4_campaign_id": campaign_id,
                    "ga4_campaign_name": campaign_name,
                    "ga4_sessions": sessions,
                    "ga4_engaged_sessions": engaged_sessions,
                    "ga4_key_events": key_events,
                    "ga4_total_revenue": total_revenue,
                }
            )

    ga4_frame = pd.DataFrame(ga4_rows)
    ads_frame = pd.DataFrame(ads_rows)
    merged_frame = merge_ga4_and_ads(ga4_frame, ads_frame)
    return ga4_frame, ads_frame, merged_frame
