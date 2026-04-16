import pathlib

base = pathlib.Path(r"c:\Users\digimkt\Downloads\GA4與ads")

# 1. Patch config.py
config_path = base / "config.py"
config_code = config_path.read_text(encoding="utf-8")

if "gsc_site_url" not in config_code:
    config_code = config_code.replace(
        "    enable_demo_data: bool",
        "    gsc_site_url: str | None\n    enable_demo_data: bool"
    )
    
    config_code = config_code.replace(
        "    def google_ads_ready(self) -> bool:",
        "    @property\n    def gsc_ready(self) -> bool:\n        has_oauth = bool(self.google_ads_client_id and self.google_ads_client_secret and self.google_ads_refresh_token)\n        return bool(self.gsc_site_url and has_oauth)\n\n    @property\n    def google_ads_ready(self) -> bool:"
    )

    config_code = config_code.replace(
        'google_ads_json_key_file_path=_resolve_path(\n            os.getenv("GOOGLE_ADS_JSON_KEY_FILE_PATH")\n        ),',
        'google_ads_json_key_file_path=_resolve_path(os.getenv("GOOGLE_ADS_JSON_KEY_FILE_PATH")),\n        gsc_site_url=os.getenv("GSC_SITE_URL"),'
    )
    # in case formatted differently
    config_code = config_code.replace(
        'google_ads_json_key_file_path=_resolve_path(os.getenv("GOOGLE_ADS_JSON_KEY_FILE_PATH")),',
        'google_ads_json_key_file_path=_resolve_path(os.getenv("GOOGLE_ADS_JSON_KEY_FILE_PATH")),\n        gsc_site_url=os.getenv("GSC_SITE_URL"),'
    )

    config_path.write_text(config_code, encoding="utf-8")

# 2. Patch setup_helpers.py
setup_path = base / "setup_helpers.py"
setup_code = setup_path.read_text(encoding="utf-8")

if "GSC_SCOPE" not in setup_code:
    setup_code = setup_code.replace(
        'GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"',
        'GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"\nGSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"'
    )
    
    # Needs to handle mode="gsc" and sites fetching
    # We will replace unified_google_login_and_fetch entirely
    
    old_unified = """def unified_google_login_and_fetch"""
    
    # We will just write a new script that replaces the whole function
    # It's safer to read from file and replace lines manually or regex.
    pass

import re
old_setup_func = re.search(r"def unified_google_login_and_fetch.*?\n    return \{\n        \"refresh_token\": refresh_token,\n        \"ga4_properties\": properties\n    \}", setup_code, re.DOTALL)
if old_setup_func:
    new_setup = """def unified_google_login_and_fetch(client_json_path: Path, mode: str = "both") -> dict[str, object]:
    if mode == "ga4":
        scopes = [GA4_READONLY_SCOPE]
        auth_message = "請在瀏覽器中登入 Google 帳號並授權 GA4 讀取權限：\\n{url}"
    elif mode == "ads":
        scopes = [GOOGLE_ADS_SCOPE]
        auth_message = "請在瀏覽器中登入 Google 帳號並授權 Google Ads 操作權限：\\n{url}"
    elif mode == "gsc":
        scopes = [GSC_SCOPE]
        auth_message = "請在瀏覽器中登入 Google 帳號並授權 Google Search Console 權限：\\n{url}"
    else:
        scopes = [GA4_READONLY_SCOPE, GOOGLE_ADS_SCOPE, GSC_SCOPE]
        auth_message = "請在瀏覽器中登入 Google 帳號並一同授權 Google Ads、GA4 與 GSC 權限：\\n{url}"

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

    return result"""
    setup_code = setup_code[:old_setup_func.start()] + new_setup + setup_code[old_setup_func.end():]
    setup_path.write_text(setup_code, encoding="utf-8")


# 3. Patch app.py (Part 1: imports and sidebar)
app_path = base / "app.py"
app_code = app_path.read_text(encoding="utf-8")

if "fetch_gsc_daily_report" not in app_code:
    app_code = app_code.replace(
        "from ga4_client import fetch_ga4_campaign_report",
        "from ga4_client import fetch_ga4_campaign_report\nfrom gsc_client import fetch_gsc_daily_report, fetch_gsc_query_report"
    )
    
app_code = app_code.replace(
    '        if config.google_ads_ready:\n            st.success("Google Ads 已就緒")\n        else:\n            st.warning("Google Ads 客戶 ID / 開發人員權杖 / 授權尚未完成")',
    '        if config.google_ads_ready:\n            st.success("Google Ads 已就緒")\n        else:\n            st.warning("Google Ads 客戶 ID / 開發人員權杖 / 授權尚未完成")\n\n        if config.gsc_ready:\n            st.success("GSC 已就緒")\n        else:\n            st.warning("GSC 網址 / 授權尚未完成")'
)

# Replace data loading
app_code = app_code.replace(
    'if not config.ga4_ready and not config.google_ads_ready:',
    'if not config.ga4_ready and not config.google_ads_ready and not config.gsc_ready:'
)
app_code = app_code.replace(
    '            raise ValueError(\n                "正式模式需要至少具備 GA4 或 Google Ads 其中之一的憑證。"\n                "請先在設定精靈補齊，或重新開啟示範資料。"\n            )',
    '            raise ValueError(\n                "正式模式需要至少具備 GA4、Google Ads 或 GSC 其中之一的憑證。"\n                "請先在設定精靈補齊，或重新開啟示範資料。"\n            )'
)

data_loader_regex = re.search(r'        if config\.ga4_ready:.*?merged_frame = merge_ga4_and_ads\(ga4_frame, ads_frame\)', app_code, re.DOTALL)
if data_loader_regex:
    new_data_loader = """        if config.ga4_ready:
            ga4_frame = fetch_ga4_campaign_report(config, start_date, end_date)
        else:
            ga4_frame = pd.DataFrame()
            messages.append("⚠️ 尚未完成 GA4 憑證設定，目前隱藏 GA4 相關數據。")

        if config.google_ads_ready:
            ads_frame = fetch_ads_campaign_report(config, start_date, end_date)
        else:
            ads_frame = pd.DataFrame()
            messages.append("⚠️ 尚未完成 Google Ads 權杖授權，目前隱藏 Ads 相關數據。")

        if config.gsc_ready:
            gsc_daily = fetch_gsc_daily_report(config, start_date, end_date)
            gsc_queries = fetch_gsc_query_report(config, start_date, end_date)
        else:
            gsc_daily = pd.DataFrame()
            gsc_queries = pd.DataFrame()
            messages.append("⚠️ 尚未完成 GSC 授權，目前隱藏自然搜尋數據。")

        merged_frame = merge_ga4_and_ads(ga4_frame, ads_frame)"""
    
    app_code = app_code[:data_loader_regex.start()] + new_data_loader + app_code[data_loader_regex.end():]

# Return gsc data in dict
app_code = app_code.replace(
    '"merged": merged_frame,\n        }',
    '"merged": merged_frame,\n            "gsc_daily": gsc_daily,\n            "gsc_queries": gsc_queries,\n        }'
)
app_code = app_code.replace(
    'ga4_frame, ads_frame, merged_frame = build_demo_data(start_date, end_date)\n        return {\n            "mode": "demo",\n            "messages": [\n                "目前缺少正式 API 憑證，因此畫面顯示的是示範資料。"\n            ],\n            "ga4": ga4_frame,\n            "ads": ads_frame,\n            "merged": merged_frame,\n        }',
    'ga4_frame, ads_frame, merged_frame = build_demo_data(start_date, end_date)\n        return {\n            "mode": "demo",\n            "messages": [\n                "目前缺少正式 API 憑證，因此畫面顯示的是示範資料。"\n            ],\n            "ga4": ga4_frame,\n            "ads": ads_frame,\n            "merged": merged_frame,\n            "gsc_daily": pd.DataFrame(),\n            "gsc_queries": pd.DataFrame(),\n        }'
)

app_path.write_text(app_code, encoding="utf-8")
print("Patch script applied core GSC loading logic.")
