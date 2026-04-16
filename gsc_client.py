import pandas as pd
from datetime import date
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import AppConfig

GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

def _build_gsc_service(config: AppConfig):
    if not config.google_ads_refresh_token or not config.google_ads_client_id:
        raise ValueError("缺少 OAuth 更新權杖或 Client ID，無法建立 GSC 連線。")
        
    credentials = Credentials(
        token=None,
        refresh_token=config.google_ads_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.google_ads_client_id,
        client_secret=config.google_ads_client_secret,
        scopes=[GSC_SCOPE],
    )
    return build("searchconsole", "v1", credentials=credentials)

def fetch_gsc_daily_report(config: AppConfig, site_url: str, start_date: date, end_date: date) -> pd.DataFrame:
    if not site_url:
        raise ValueError("GSC_SITE_URL is missing.")
        
    service = _build_gsc_service(config)
    request = {
        "startDate": str(start_date),
        "endDate": str(end_date),
        "dimensions": ["date"],
        "rowLimit": 25000,
    }
    
    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    rows = response.get("rows", [])
    
    parsed_rows = []
    for r in rows:
        parsed_rows.append({
            "date": r["keys"][0],
            "gsc_clicks": r.get("clicks", 0),
            "gsc_impressions": r.get("impressions", 0),
            "gsc_ctr": r.get("ctr", 0.0),
            "gsc_position": r.get("position", 0.0),
        })
        
    if not parsed_rows:
        return pd.DataFrame({
            "date": pd.Series(dtype="datetime64[ns]"),
            "gsc_clicks": pd.Series(dtype="float64"),
            "gsc_impressions": pd.Series(dtype="float64"),
            "gsc_ctr": pd.Series(dtype="float64"),
            "gsc_position": pd.Series(dtype="float64"),
        })

    df = pd.DataFrame(parsed_rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["gsc_clicks", "gsc_impressions", "gsc_ctr", "gsc_position"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df

def fetch_gsc_query_report(config: AppConfig, site_url: str, start_date: date, end_date: date, top_n: int = 50) -> pd.DataFrame:
    if not site_url:
        raise ValueError("GSC_SITE_URL is missing.")
        
    service = _build_gsc_service(config)
    request = {
        "startDate": str(start_date),
        "endDate": str(end_date),
        "dimensions": ["query"],
        "rowLimit": top_n,
    }
    
    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    rows = response.get("rows", [])
    
    parsed_rows = []
    for r in rows:
        parsed_rows.append({
            "query": r["keys"][0],
            "gsc_clicks": r.get("clicks", 0),
            "gsc_impressions": r.get("impressions", 0),
            "gsc_ctr": r.get("ctr", 0.0),
            "gsc_position": r.get("position", 0.0),
        })
        
    if not parsed_rows:
        return pd.DataFrame({
            "query": pd.Series(dtype="object"),
            "gsc_clicks": pd.Series(dtype="float64"),
            "gsc_impressions": pd.Series(dtype="float64"),
            "gsc_ctr": pd.Series(dtype="float64"),
            "gsc_position": pd.Series(dtype="float64"),
        })

    df = pd.DataFrame(parsed_rows)
    for col in ["gsc_clicks", "gsc_impressions", "gsc_ctr", "gsc_position"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df
