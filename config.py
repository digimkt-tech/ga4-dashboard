from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent


def _read_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _resolve_path(value: str | None) -> Path | None:
    if not value:
        return None

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path

    return path.resolve()


def _clean_property_id(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = value.strip()
    if cleaned.startswith("properties/"):
        return cleaned.split("/", maxsplit=1)[1]
    return cleaned


def _clean_customer_id(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = value.strip().replace("-", "")
    return cleaned or None


def _default_ads_config_path() -> Path | None:
    default_path = BASE_DIR / "google-ads.yaml"
    return default_path if default_path.exists() else None


def _read_oauth_client_info(path: Path | None) -> tuple[str | None, str | None]:
    if not path or not path.exists():
        return None, None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None

    client_section = payload.get("installed") or payload.get("web") or {}
    client_id = client_section.get("client_id")
    client_secret = client_section.get("client_secret")
    return client_id, client_secret


@dataclass(frozen=True)
class AppConfig:
    ga4_property_id: str | None
    ga4_credentials_path: Path | None
    ga4_campaign_id_dimension: str
    ga4_campaign_dimension: str
    google_ads_customer_id: str | None
    google_ads_login_customer_id: str | None
    google_ads_config_path: Path | None
    google_ads_developer_token: str | None
    google_ads_oauth_client_json_path: Path | None
    google_ads_client_id: str | None
    google_ads_client_secret: str | None
    google_ads_refresh_token: str | None
    google_ads_json_key_file_path: Path | None
    gsc_site_url: str | None
    enable_demo_data: bool
    default_lookback_days: int

    @property
    def effective_ga4_credentials_path(self) -> Path | None:
        if self.ga4_credentials_path and self.ga4_credentials_path.exists():
            return self.ga4_credentials_path

        fallback = _resolve_path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        if fallback and fallback.exists():
            return fallback

        return None

    @property
    def ga4_ready(self) -> bool:
        has_credentials = bool(self.effective_ga4_credentials_path)
        has_oauth = bool(self.google_ads_client_id and self.google_ads_client_secret and self.google_ads_refresh_token)
        return bool(self.ga4_property_id and (has_credentials or has_oauth))

    @property
    def gsc_ready(self) -> bool:
        has_oauth = bool(self.google_ads_client_id and self.google_ads_client_secret and self.google_ads_refresh_token)
        return bool(self.gsc_site_url and has_oauth)

    @property
    def google_ads_ready(self) -> bool:
        if not self.google_ads_customer_id:
            return False

        if self.google_ads_config_path and self.google_ads_config_path.exists():
            return True

        if not self.google_ads_developer_token:
            return False

        oauth_ready = all(
            [
                self.google_ads_client_id,
                self.google_ads_client_secret,
                self.google_ads_refresh_token,
            ]
        )
        service_account_ready = bool(
            self.google_ads_json_key_file_path
            and self.google_ads_json_key_file_path.exists()
        )
        return oauth_ready or service_account_ready

    def google_ads_config_dict(self) -> dict[str, object] | None:
        if not self.google_ads_developer_token:
            return None

        config: dict[str, object] = {
            "developer_token": self.google_ads_developer_token,
            "use_proto_plus": True,
        }

        if self.google_ads_login_customer_id:
            config["login_customer_id"] = self.google_ads_login_customer_id

        if (
            self.google_ads_json_key_file_path
            and self.google_ads_json_key_file_path.exists()
        ):
            config["json_key_file_path"] = str(self.google_ads_json_key_file_path)
            return config

        if all(
            [
                self.google_ads_client_id,
                self.google_ads_client_secret,
                self.google_ads_refresh_token,
            ]
        ):
            config.update(
                {
                    "client_id": self.google_ads_client_id,
                    "client_secret": self.google_ads_client_secret,
                    "refresh_token": self.google_ads_refresh_token,
                }
            )
            return config

        return None

    def credential_status(self) -> dict[str, str]:
        return {
            "ga4": "ready" if self.ga4_ready else "missing",
            "google_ads": "ready" if self.google_ads_ready else "missing",
        }


def _load_streamlit_secrets() -> None:
    """在 Streamlit Cloud 上執行時，把 st.secrets 的值注入成環境變數。"""
    try:
        import streamlit as st
        for key, value in st.secrets.items():
            if isinstance(value, str) and key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass


def load_config() -> AppConfig:
    _load_streamlit_secrets()
    load_dotenv(BASE_DIR / ".env", override=False)
    configured_ads_path = _resolve_path(os.getenv("GOOGLE_ADS_CONFIG_PATH"))
    oauth_client_json_path = _resolve_path(os.getenv("GOOGLE_ADS_OAUTH_CLIENT_JSON_PATH"))
    oauth_client_id, oauth_client_secret = _read_oauth_client_info(
        oauth_client_json_path
    )

    return AppConfig(
        ga4_property_id=_clean_property_id(os.getenv("GA4_PROPERTY_ID")),
        ga4_credentials_path=_resolve_path(os.getenv("GA4_CREDENTIALS_PATH")),
        ga4_campaign_id_dimension=os.getenv(
            "GA4_CAMPAIGN_ID_DIMENSION", "sessionGoogleAdsCampaignId"
        ),
        ga4_campaign_dimension=os.getenv(
            "GA4_CAMPAIGN_DIMENSION", "sessionGoogleAdsCampaignName"
        ),
        google_ads_customer_id=_clean_customer_id(os.getenv("GOOGLE_ADS_CUSTOMER_ID")),
        google_ads_login_customer_id=_clean_customer_id(
            os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
        ),
        google_ads_config_path=configured_ads_path or _default_ads_config_path(),
        google_ads_developer_token=os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        google_ads_oauth_client_json_path=oauth_client_json_path,
        google_ads_client_id=os.getenv("GOOGLE_ADS_CLIENT_ID") or oauth_client_id,
        google_ads_client_secret=os.getenv("GOOGLE_ADS_CLIENT_SECRET")
        or oauth_client_secret,
        google_ads_refresh_token=os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        google_ads_json_key_file_path=_resolve_path(os.getenv("GOOGLE_ADS_JSON_KEY_FILE_PATH")),
        gsc_site_url=os.getenv("GSC_SITE_URL"),
        enable_demo_data=_read_bool("ENABLE_DEMO_DATA", default=True),
        default_lookback_days=max(1, _read_int("DEFAULT_LOOKBACK_DAYS", default=30)),
    )
