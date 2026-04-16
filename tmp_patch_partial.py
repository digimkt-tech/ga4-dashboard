import pathlib

app_path = pathlib.Path(r"c:\Users\digimkt\Downloads\GA4與ads\app.py")
content = app_path.read_text(encoding="utf-8")

old_code = """def load_dashboard_data(
    config: AppConfig,
    start_date: date,
    end_date: date,
    use_demo: bool,
) -> dict[str, object]:
    if not config.ga4_ready or not config.google_ads_ready:
        if not use_demo:
            raise ValueError(
                "正式模式需要同時具備 GA4 與 Google Ads 憑證。"
                "請先在設定精靈補齊，或重新開啟示範資料。"
            )

        ga4_frame, ads_frame, merged_frame = build_demo_data(start_date, end_date)
        return {
            "mode": "demo",
            "messages": [
                "目前缺少正式 API 憑證，因此畫面顯示的是示範資料。"
            ],
            "ga4": ga4_frame,
            "ads": ads_frame,
            "merged": merged_frame,
        }

    try:
        ga4_frame = fetch_ga4_campaign_report(config, start_date, end_date)
        ads_frame = fetch_ads_campaign_report(config, start_date, end_date)
        merged_frame = merge_ga4_and_ads(ga4_frame, ads_frame)
        return {
            "mode": "live",
            "messages": [],
            "ga4": ga4_frame,
            "ads": ads_frame,
            "merged": merged_frame,
        }
    except Exception as exc:"""

new_code = """def load_dashboard_data(
    config: AppConfig,
    start_date: date,
    end_date: date,
    use_demo: bool,
) -> dict[str, object]:
    if not config.ga4_ready and not config.google_ads_ready:
        if not use_demo:
            raise ValueError(
                "正式模式需要至少具備 GA4 或 Google Ads 其中之一的憑證。"
                "請先在設定精靈補齊，或重新開啟示範資料。"
            )

        ga4_frame, ads_frame, merged_frame = build_demo_data(start_date, end_date)
        return {
            "mode": "demo",
            "messages": [
                "目前缺少正式 API 憑證，因此畫面顯示的是示範資料。"
            ],
            "ga4": ga4_frame,
            "ads": ads_frame,
            "merged": merged_frame,
        }

    try:
        messages = []
        if config.ga4_ready:
            ga4_frame = fetch_ga4_campaign_report(config, start_date, end_date)
        else:
            ga4_frame = pd.DataFrame()
            messages.append("⚠️ 尚未完成 GA4 憑證設定，目前隱藏 GA4 相關數據。")

        if config.google_ads_ready:
            ads_frame = fetch_ads_campaign_report(config, start_date, end_date)
        else:
            ads_frame = pd.DataFrame()
            messages.append("⚠️ 尚未完成 Google Ads 權杖授權，目前隱藏 Ads 相關數據。")

        merged_frame = merge_ga4_and_ads(ga4_frame, ads_frame)
        
        return {
            "mode": "live",
            "messages": messages,
            "ga4": ga4_frame,
            "ads": ads_frame,
            "merged": merged_frame,
        }
    except Exception as exc:"""

content = content.replace(old_code, new_code)
app_path.write_text(content, encoding="utf-8")
print("Done")
