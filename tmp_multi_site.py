import pathlib
import sys
import os

base = pathlib.Path(r"c:\Users\digimkt\Downloads\GA4與ads")

# 1. Update ga4_client.py
ga4_path = base / "ga4_client.py"
ga4_code = ga4_path.read_text(encoding="utf-8")
ga4_code = ga4_code.replace(
    "def fetch_ga4_campaign_report(\n    config: AppConfig,\n    start_date: date,\n    end_date: date,\n) -> pd.DataFrame:",
    "def fetch_ga4_campaign_report(\n    config: AppConfig,\n    property_id: str,\n    start_date: date,\n    end_date: date,\n) -> pd.DataFrame:"
)
ga4_code = ga4_code.replace(
    "property=f\"properties/{config.ga4_property_id}\",",
    "property=f\"properties/{property_id}\","
)
ga4_code = ga4_code.replace(
    "    if not config.ga4_property_id:",
    "    if not property_id:"
)
ga4_path.write_text(ga4_code, encoding="utf-8")


# 2. Update gsc_client.py
gsc_path = base / "gsc_client.py"
gsc_code = gsc_path.read_text(encoding="utf-8")
gsc_code = gsc_code.replace(
    "def fetch_gsc_daily_report(config: AppConfig, start_date: date, end_date: date) -> pd.DataFrame:",
    "def fetch_gsc_daily_report(config: AppConfig, site_url: str, start_date: date, end_date: date) -> pd.DataFrame:"
)
gsc_code = gsc_code.replace(
    "    if not config.gsc_site_url:\n        raise ValueError(\"GSC_SITE_URL is missing.\")",
    "    if not site_url:\n        raise ValueError(\"GSC_SITE_URL is missing.\")"
)
gsc_code = gsc_code.replace("siteUrl=config.gsc_site_url", "siteUrl=site_url")

gsc_code = gsc_code.replace(
    "def fetch_gsc_query_report(config: AppConfig, start_date: date, end_date: date, top_n: int = 50) -> pd.DataFrame:",
    "def fetch_gsc_query_report(config: AppConfig, site_url: str, start_date: date, end_date: date, top_n: int = 50) -> pd.DataFrame:"
)
gsc_path.write_text(gsc_code, encoding="utf-8")


# 3. App.py rewriting
app_path = base / "app.py"
app_code = app_path.read_text(encoding="utf-8")

if "from sites_manager import" not in app_code:
    app_code = "from sites_manager import load_sites, add_site, remove_site, SiteConfig\n" + app_code


# 3.1 Setup UI Override
def replace_setup_ui(code):
    start_str = 'st.markdown("#### 1. 綁定 GA4 資源")'
    end_str = 'st.markdown("#### 3. 綁定 Google Search Console 網站 (GSC)")'
    
    start_idx = code.find(start_str)
    if start_idx == -1: return code
    end_idx = code.find(end_str, start_idx)
    if end_idx == -1: return code
    # Find the end of the block to replace entirely
    end_idx = code.find('st.markdown("---")', end_idx)
    if end_idx == -1: return code
    
    new_setup_ui = """
    st.markdown("### 🌐 多網域/網站組合管理 (Site Manager)")
    st.info("在此您可以建立並綁定多個網站。系統會自動抓取所有綁定網站的資料，讓您能在儀表板中同時查看。")
    
    existing_sites = load_sites()
    if existing_sites:
        import pandas as pd
        site_df = pd.DataFrame([{"網站名稱": s.domain_name, "GA4 ID": s.ga4_property_id, "GSC 網址": s.gsc_site_url} for s in existing_sites])
        st.dataframe(site_df, use_container_width=True, hide_index=True)
        
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            del_site_val = st.selectbox("選擇要移除的網站", [s.domain_name for s in existing_sites])
        with del_col2:
            st.write("")
            st.write("")
            if st.button("🗑️ 移除網站", use_container_width=True):
                remove_site(del_site_val)
                st.rerun()
                
    st.markdown("#### ➕ 新增網站")
    with st.container(border=True):
        new_domain = st.text_input("自訂網站名稱 (例如: 首頁官網)")
        
        ga4_choices = st.session_state.get("ga4_property_choices", [])
        gsc_choices = st.session_state.get("gsc_sites", [])
        
        if ga4_choices and gsc_choices:
            new_ga4 = st.selectbox("選擇 GA4 資源", ga4_choices, format_func=lambda x: f"{x['account_display_name']} > {x['property_display_name']} ({x['property_id']})")
            new_gsc = st.selectbox("選擇 GSC 資源", gsc_choices)
            
            if st.button("儲存並加入網站組合 (Add Site)", type="primary"):
                if new_domain:
                    add_site(new_domain, new_ga4["property_id"], new_gsc)
                    st.success(f"已加入網站: {new_domain}")
                    st.rerun()
                else:
                    st.error("請填寫網站名稱！")
        else:
            st.warning("請先使用上方的「一鍵綜合登入」取得您的 GA4 與 GSC 清單，才能新增網站對應。")
"""
    return code[:start_idx] + new_setup_ui + code[end_idx:]

app_code = replace_setup_ui(app_code)


# 3.2 Main Dashboard Loader Override
# Find load_dashboard_data function and replace
import re
loader_match = re.search(r"def load_dashboard_data\(.*?\n        }", app_code, re.DOTALL)
if loader_match:
    new_loader = """import pandas as pd
def load_dashboard_data(
    config: AppConfig,
    sites: list[SiteConfig],
    start_date: date,
    end_date: date,
    use_demo: bool,
) -> dict[str, object]:
    if not sites and not config.google_ads_ready:
        if not use_demo:
            raise ValueError(
                "尚無任何網站資料！請先在設定精靈新增網站，或開啟示範資料。"
            )
        ga4_frame, ads_frame, merged_frame = build_demo_data(start_date, end_date)
        return {
            "mode": "demo",
            "messages": ["目前缺少正式網站設定，顯示示範資料。"],
            "ga4": ga4_frame,
            "ads": ads_frame,
            "merged": merged_frame,
            "gsc_daily": pd.DataFrame(),
            "gsc_queries": pd.DataFrame(),
        }

    try:
        messages = []
        all_ga4 = []
        all_ads = []
        all_gsc_daily = []
        all_gsc_queries = []
        
        # Load Ads Data (Global)
        if config.google_ads_ready:
            global_ads = fetch_ads_campaign_report(config, start_date, end_date)
        else:
            global_ads = pd.DataFrame()
            messages.append("⚠️ Google Ads 尚未設定。")
            
        from ga4_client import _build_client as ga4_client_builder
        ga4_has_auth = config.effective_ga4_credentials_path or (config.google_ads_client_id and config.google_ads_client_secret and config.google_ads_refresh_token)

        if not ga4_has_auth:
            messages.append("⚠️ GA4 尚未獲得授權，跳過所有 GA4 讀取。")
            
        for site in sites:
            # GA4
            if ga4_has_auth and site.ga4_property_id:
                try:
                    vf = fetch_ga4_campaign_report(config, site.ga4_property_id, start_date, end_date)
                    vf["domain"] = site.domain_name
                    all_ga4.append(vf)
                except Exception as e:
                    messages.append(f"讀取 {site.domain_name} GA4 失敗: {e}")
            
            # GSC
            if site.gsc_site_url and config.google_ads_client_id:
                try:
                    gd = fetch_gsc_daily_report(config, site.gsc_site_url, start_date, end_date)
                    gq = fetch_gsc_query_report(config, site.gsc_site_url, start_date, end_date)
                    if not gd.empty: gd["domain"] = site.domain_name
                    if not gq.empty: gq["domain"] = site.domain_name
                    all_gsc_daily.append(gd)
                    all_gsc_queries.append(gq)
                except Exception as e:
                    messages.append(f"讀取 {site.domain_name} GSC 失敗: {e}")

        final_ga4 = pd.concat(all_ga4, ignore_index=True) if all_ga4 else pd.DataFrame()
        final_gsc_daily = pd.concat(all_gsc_daily, ignore_index=True) if all_gsc_daily else pd.DataFrame()
        final_gsc_queries = pd.concat(all_gsc_queries, ignore_index=True) if all_gsc_queries else pd.DataFrame()
        
        # In a multi-domain setup, we merge ALL GA4 with GLOBAL Ads. 
        # (Since ads usually apply to the whole business unless campaign matches perfectly)
        merged_frame = merge_ga4_and_ads(final_ga4, global_ads)

        return {
            "mode": "live",
            "messages": messages,
            "ga4": final_ga4,
            "ads": global_ads,
            "merged": merged_frame,
            "gsc_daily": final_gsc_daily,
            "gsc_queries": final_gsc_queries,
        }
    except Exception as exc:
        if not use_demo:
            raise RuntimeError(f"載入失敗：{exc}") from exc
        ga4_frame, ads_frame, merged_frame = build_demo_data(start_date, end_date)
        return {
            "mode": "demo",
            "messages": [f"正式 API 載入失敗，已暫時切回示範資料。詳細原因：{exc}"],
            "ga4": ga4_frame,
            "ads": ads_frame,
            "merged": merged_frame,
            "gsc_daily": pd.DataFrame(),
            "gsc_queries": pd.DataFrame(),
        }"""
    app_code = app_code[:loader_match.start()] + new_loader + app_code[loader_match.end():]


# 3.3 Main Data Fetch pipeline
app_code = app_code.replace(
    'dashboard_payload = load_dashboard_data(config, start_date, end_date, use_demo)',
    'sites = load_sites()\n                dashboard_payload = load_dashboard_data(config, sites, start_date, end_date, use_demo)'
)


# 3.4 UI Filter for Domain
def add_domain_filter(code):
    mark = 'st.markdown("## 目前對齊維度")'
    idx = code.find(mark)
    if idx == -1: return code
    filter_ui = """
        st.markdown("## 網域分析切換")
        sites = load_sites()
        domain_options = ["全部網域 (All)"] + [s.domain_name for s in sites]
        selected_domain = st.selectbox("選擇要獨立檢視的網站", domain_options, key="domain_filter")
        
    """
    return code[:idx] + filter_ui + code[idx:]

app_code = add_domain_filter(app_code)


# 3.5 Apply filter to data before rendering
def apply_filter(code):
    mark = 'if not payload["merged"].empty:'
    idx = code.find(mark)
    if idx == -1: return code
    filter_logic = """
    sel_domain = st.session_state.get("domain_filter", "全部網域 (All)")
    
    # Filter payload
    if sel_domain != "全部網域 (All)":
        if "domain" in payload["ga4"].columns and not payload["ga4"].empty:
            payload["ga4"] = payload["ga4"][payload["ga4"]["domain"] == sel_domain]
        if "domain" in payload["gsc_daily"].columns and not payload["gsc_daily"].empty:
            payload["gsc_daily"] = payload["gsc_daily"][payload["gsc_daily"]["domain"] == sel_domain]
        if "domain" in payload["gsc_queries"].columns and not payload["gsc_queries"].empty:
            payload["gsc_queries"] = payload["gsc_queries"][payload["gsc_queries"]["domain"] == sel_domain]
        # Re-merge
        payload["merged"] = merge_ga4_and_ads(payload["ga4"], payload["ads"])
        
    """
    return code[:idx] + filter_logic + code[idx:]

app_code = apply_filter(app_code)

app_path.write_text(app_code, encoding="utf-8")
print("Refactored successfully for multi-tenant")
