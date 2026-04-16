from __future__ import annotations

from pathlib import Path
from typing import Sequence

import requests
from google.ads.googleads.client import GoogleAdsClient
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from config import AppConfig, BASE_DIR


ENV_PATH = BASE_DIR / ".env"
GA4_READONLY_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


def update_env_values(updates: dict[str, str | None]) -> Path:
    ENV_PATH.touch(exist_ok=True)
    existing_lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    sanitized = {
        key: ("" if value is None else str(value).strip())
        for key, value in updates.items()
    }

    written_keys: set[str] = set()
    output_lines: list[str] = []

    for line in existing_lines:
        if "=" not in line or line.lstrip().startswith("#"):
            output_lines.append(line)
            continue

        key, _ = line.split("=", maxsplit=1)
        if key in sanitized:
            output_lines.append(f"{key}={sanitized[key]}")
            written_keys.add(key)
        else:
            output_lines.append(line)

    for key, value in sanitized.items():
        if key not in written_keys:
            output_lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(output_lines).rstrip() + "\n", encoding="utf-8")
    return ENV_PATH


def save_bytes_file(content: bytes, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return destination


def _build_flow(client_json_path: Path, scopes: Sequence[str]) -> InstalledAppFlow:
    if not client_json_path.exists():
        raise FileNotFoundError(f"找不到 OAuth 用戶端 JSON：{client_json_path}")

    return InstalledAppFlow.from_client_secrets_file(
        str(client_json_path),
        scopes=list(scopes),
    )


def run_local_google_login(
    client_json_path: Path,
    scopes: Sequence[str],
    authorization_prompt_message: str,
    success_message: str,
):
    flow = _build_flow(client_json_path, scopes)
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        authorization_prompt_message=authorization_prompt_message,
        success_message=success_message,
        open_browser=True,
        access_type="offline",
        prompt="consent",
    )
    return credentials


def get_google_ads_refresh_token(client_json_path: Path) -> str:
    credentials = run_local_google_login(
        client_json_path=client_json_path,
        scopes=[GOOGLE_ADS_SCOPE],
        authorization_prompt_message=(
            "請在瀏覽器中登入 Google 帳號並完成 Google Ads 授權：\n{url}"
        ),
        success_message="Google Ads 授權完成，請回到應用程式。",
    )
    refresh_token = credentials.refresh_token or ""
    if not refresh_token:
        raise RuntimeError(
            "這次授權沒有回傳 refresh token。請確認授權畫面有要求離線存取，"
            "並重新執行一次。"
        )
    return refresh_token


def list_ga4_properties_via_google_login(client_json_path: Path) -> list[dict[str, str]]:
    credentials = run_local_google_login(
        client_json_path=client_json_path,
        scopes=[GA4_READONLY_SCOPE],
        authorization_prompt_message=(
            "請在瀏覽器中登入 Google 帳號並授權讀取 GA4 資源：\n{url}"
        ),
        success_message="GA4 授權完成，請回到應用程式。",
    )

    if not credentials.valid:
        credentials.refresh(Request())

    url = "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"
    headers = {"Authorization": f"Bearer {credentials.token}"}
    properties: list[dict[str, str]] = []
    page_token = ""

    while True:
        params = {"pageSize": 200}
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        for account_summary in payload.get("accountSummaries", []):
            account_name = account_summary.get("displayName", "")
            account_resource = account_summary.get("name", "")
            for property_summary in account_summary.get("propertySummaries", []):
                property_resource = property_summary.get("property", "")
                properties.append(
                    {
                        "account_display_name": account_name,
                        "account_resource_name": account_resource,
                        "property_display_name": property_summary.get(
                            "displayName", ""
                        ),
                        "property_resource_name": property_resource,
                        "property_id": property_resource.split("/")[-1]
                        if property_resource
                        else "",
                        "property_type": property_summary.get("propertyType", ""),
                        "parent": property_summary.get("parent", ""),
                    }
                )

        page_token = payload.get("nextPageToken", "")
        if not page_token:
            break

    properties.sort(
        key=lambda item: (
            item["account_display_name"].lower(),
            item["property_display_name"].lower(),
        )
    )
    return properties


def list_accessible_google_ads_customers(config: AppConfig) -> list[str]:
    config_dict = config.google_ads_config_dict()
    if not config_dict:
        raise RuntimeError(
            "列出 Google Ads 客戶 ID 前，需要先有 Developer Token、"
            "OAuth 用戶端資訊，以及 Refresh Token。"
        )

    client = GoogleAdsClient.load_from_dict(config_dict)
    customer_service = client.get_service("CustomerService")
    response = customer_service.list_accessible_customers()
    return [
        resource_name.split("/")[-1]
        for resource_name in response.resource_names
        if resource_name
    ]

def unified_google_login_and_fetch(client_json_path: Path, mode: str = "both") -> dict[str, object]:
    if mode == "ga4":
        scopes = [GA4_READONLY_SCOPE]
        auth_message = "請在瀏覽器中登入 Google 帳號並授權 GA4 讀取權限：\n{url}"
    elif mode == "ads":
        scopes = [GOOGLE_ADS_SCOPE]
        auth_message = "請在瀏覽器中登入 Google 帳號並授權 Google Ads 操作權限：\n{url}"
    elif mode == "gsc":
        scopes = [GSC_SCOPE]
        auth_message = "請在瀏覽器中登入 Google 帳號並授權 Google Search Console 權限：\n{url}"
    else:
        scopes = [GA4_READONLY_SCOPE, GOOGLE_ADS_SCOPE, GSC_SCOPE]
        auth_message = "請在瀏覽器中登入 Google 帳號並一同授權 Google Ads、GA4 與 GSC 權限：\n{url}"

    credentials = run_local_google_login(
        client_json_path=client_json_path,
        scopes=scopes,
        authorization_prompt_message=auth_message,
        success_message="授權完成，請回到應用程式。",
    )
    if not credentials.valid:
        credentials.refresh(Request())

    refresh_token = credentials.refresh_token or ""
    
    result = {"refresh_token": refresh_token, "ga4_properties": [], "gsc_sites": []}

    if mode in ("ga4", "both", "all"):
        url = "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"
        headers = {"Authorization": f"Bearer {credentials.token}"}
        page_token = ""
        properties = []
        while True:
            params = {"pageSize": 200}
            if page_token: params["pageToken"] = page_token
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                payload = response.json()
                for account_summary in payload.get("accountSummaries", []):
                    account_name = account_summary.get("displayName", "")
                    for property_summary in account_summary.get("propertySummaries", []):
                        prop = property_summary.get("property", "")
                        properties.append({
                            "account_display_name": account_name,
                            "property_display_name": property_summary.get("displayName", ""),
                            "property_id": prop.split("/")[-1] if prop else "",
                            "property_type": property_summary.get("propertyType", ""),
                        })
                page_token = payload.get("nextPageToken", "")
                if not page_token: break
            else:
                break
        properties.sort(key=lambda item: (item["account_display_name"].lower(), item["property_display_name"].lower()))
        result["ga4_properties"] = properties

    if mode in ("gsc", "both", "all"):
        url_gsc = "https://www.googleapis.com/webmasters/v3/sites"
        headers_gsc = {"Authorization": f"Bearer {credentials.token}"}
        response_gsc = requests.get(url_gsc, headers=headers_gsc, timeout=30)
        sites = []
        if response_gsc.status_code == 200:
            site_entries = response_gsc.json().get("siteEntry", [])
            for s in site_entries:
                sites.append(s.get("siteUrl", ""))
        sites.sort()
        result["gsc_sites"] = sites

    return result
