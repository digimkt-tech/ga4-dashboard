from __future__ import annotations

from config import load_config
from setup_helpers import get_google_ads_refresh_token


def main() -> None:
    config = load_config()

    if not config.google_ads_oauth_client_json_path:
        raise SystemExit(
            "`.env` 裡找不到 `GOOGLE_ADS_OAUTH_CLIENT_JSON_PATH`，"
            "請先指向您下載好的 OAuth 用戶端 JSON。"
        )

    if not config.google_ads_oauth_client_json_path.exists():
        raise SystemExit(
            "找不到 OAuth 用戶端 JSON："
            f"{config.google_ads_oauth_client_json_path}"
        )

    refresh_token = get_google_ads_refresh_token(
        config.google_ads_oauth_client_json_path
    )

    print("Google Ads Refresh Token：")
    print(refresh_token)
    print("")
    print("請把下面這一行寫進 `.env`：")
    print(f"GOOGLE_ADS_REFRESH_TOKEN={refresh_token}")


if __name__ == "__main__":
    main()
