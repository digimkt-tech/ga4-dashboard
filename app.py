from __future__ import annotations
from sites_manager import load_sites, add_site, remove_site, SiteConfig

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from ads_client import fetch_ads_campaign_report
from config import AppConfig, BASE_DIR, load_config
from data_processor import (
    build_campaign_summary,
    build_daily_summary,
    build_demo_data,
    merge_ga4_and_ads,
    summarize_dashboard,
)
from ga4_client import fetch_ga4_campaign_report
from gsc_client import fetch_gsc_daily_report, fetch_gsc_query_report
from setup_helpers import (
    unified_google_login_and_fetch,
    get_google_ads_refresh_token,
    list_accessible_google_ads_customers,
    list_ga4_properties_via_google_login,
    save_bytes_file,
    update_env_values,
)


st.set_page_config(
    page_title="GA4 與 Google Ads 分析儀表板",
    layout="wide",
)


METRIC_LABELS = {
    "ads_clicks": "Ads 點擊",
    "ga4_sessions": "GA4 工作階段",
    "ga4_key_events": "GA4 關鍵事件",
    "ads_cost": "Ads 花費",
    "ga4_total_revenue": "GA4 營收",
}

COLOR_MAP = {
    "Ads 點擊": "#14b8a6",
    "GA4 工作階段": "#38bdf8",
    "GA4 關鍵事件": "#f59e0b",
    "Ads 花費": "#14b8a6",
    "GA4 營收": "#f97316",
}


def get_theme_type() -> str:
    try:
        theme_type = st.context.theme.type
        if theme_type in {"light", "dark"}:
            return theme_type
    except Exception:
        pass
    return "light"


def build_theme_css(theme_type: str) -> str:
    if theme_type == "dark":
        return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap');

:root {
  --ink: #e5eef7;
  --muted: #9fb0c3;
  --panel: rgba(17, 24, 39, 0.72);
  --panel-strong: rgba(15, 23, 42, 0.84);
  --line: rgba(148, 163, 184, 0.18);
  --shadow: 0 18px 38px rgba(2, 6, 23, 0.32);
  --hero-grad-a: rgba(14, 116, 144, 0.94);
  --hero-grad-b: rgba(30, 64, 175, 0.92);
}

html, body, [class*="css"] {
  font-family: "Noto Sans TC", sans-serif;
  color: var(--ink);
}

.stApp {
  background:
    radial-gradient(circle at 0% 0%, rgba(8, 47, 73, 0.75), transparent 26%),
    radial-gradient(circle at 100% 0%, rgba(88, 28, 135, 0.42), transparent 30%),
    linear-gradient(180deg, #020617 0%, #0f172a 100%);
}

.block-container {
  padding-top: 1.8rem;
  padding-bottom: 2rem;
}

h1, h2, h3 {
  font-family: "Space Grotesk", "Noto Sans TC", sans-serif;
  letter-spacing: -0.02em;
}

.hero-card {
  background: linear-gradient(135deg, var(--hero-grad-a), var(--hero-grad-b));
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 26px;
  padding: 1.6rem 1.7rem;
  color: #f8fafc;
  box-shadow: var(--shadow);
}

.hero-kicker {
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 0.78rem;
  opacity: 0.84;
  margin-bottom: 0.35rem;
}

.hero-copy {
  margin-top: 0.55rem;
  max-width: 760px;
  color: rgba(248, 250, 252, 0.86);
}

.setup-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 1rem 1.1rem;
  box-shadow: var(--shadow);
}

.setup-note {
  color: var(--muted);
  font-size: 0.95rem;
}

[data-testid="stMetric"] {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 0.85rem 0.95rem;
  box-shadow: var(--shadow);
}

[data-testid="stSidebar"] {
  background: rgba(2, 6, 23, 0.82);
  border-right: 1px solid var(--line);
}
</style>
"""

    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap');

:root {
  --ink: #17202b;
  --muted: #506073;
  --panel: rgba(255, 255, 255, 0.82);
  --panel-strong: rgba(255, 255, 255, 0.92);
  --line: rgba(23, 32, 43, 0.08);
  --shadow: 0 20px 45px rgba(15, 23, 42, 0.10);
  --hero-grad-a: rgba(15, 118, 110, 0.95);
  --hero-grad-b: rgba(29, 78, 216, 0.90);
}

html, body, [class*="css"] {
  font-family: "Noto Sans TC", sans-serif;
  color: var(--ink);
}

.stApp {
  background:
    radial-gradient(circle at 0% 0%, rgba(255, 237, 196, 0.85), transparent 28%),
    radial-gradient(circle at 100% 0%, rgba(191, 219, 254, 0.75), transparent 32%),
    linear-gradient(180deg, #f8fafc 0%, #eff6ff 100%);
}

.block-container {
  padding-top: 1.8rem;
  padding-bottom: 2rem;
}

h1, h2, h3 {
  font-family: "Space Grotesk", "Noto Sans TC", sans-serif;
  letter-spacing: -0.02em;
}

.hero-card {
  background: linear-gradient(135deg, var(--hero-grad-a), var(--hero-grad-b));
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 26px;
  padding: 1.6rem 1.7rem;
  color: #f8fafc;
  box-shadow: var(--shadow);
}

.hero-kicker {
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 0.78rem;
  opacity: 0.84;
  margin-bottom: 0.35rem;
}

.hero-copy {
  margin-top: 0.55rem;
  max-width: 760px;
  color: rgba(248, 250, 252, 0.88);
}

.setup-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 1rem 1.1rem;
  box-shadow: var(--shadow);
}

.setup-note {
  color: var(--muted);
  font-size: 0.95rem;
}

[data-testid="stMetric"] {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 0.85rem 0.95rem;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

[data-testid="stSidebar"] {
  background: rgba(255, 255, 255, 0.72);
  border-right: 1px solid rgba(15, 23, 42, 0.06);
}
</style>
"""


def to_project_relative(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(BASE_DIR.resolve())
        return f"./{relative.as_posix()}"
    except ValueError:
        return str(path.resolve())


def format_number(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}"


def format_ratio(value: float) -> str:
    return f"{value:,.2f}x"


def style_figure(figure, title: str, theme_type: str):
    if theme_type == "dark":
        figure.update_layout(
            title=title,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,0.68)",
            font_color="#e5eef7",
            margin=dict(l=12, r=12, t=56, b=12),
            legend_title_text="",
            hovermode="x unified",
        )
        figure.update_xaxes(showgrid=False)
        figure.update_yaxes(gridcolor="rgba(148,163,184,0.12)")
        return figure

    figure.update_layout(
        title=title,
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.82)",
        font_color="#17202b",
        margin=dict(l=12, r=12, t=56, b=12),
        legend_title_text="",
        hovermode="x unified",
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="rgba(23, 32, 43, 0.08)")
    return figure


def initialize_state(config: AppConfig) -> None:
    today = date.today()
    default_start = today - timedelta(days=config.default_lookback_days)

    st.session_state.setdefault("start_date", default_start)
    st.session_state.setdefault("end_date", today)
    st.session_state.setdefault("top_n", 10)
    st.session_state.setdefault("use_demo", config.enable_demo_data)
    st.session_state.setdefault("ga4_property_choices", [])
    st.session_state.setdefault("ads_customer_choices", [])
    st.session_state.setdefault("generated_refresh_token", "")


import pandas as pd
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

        if config.gsc_ready:
            gsc_daily = fetch_gsc_daily_report(config, start_date, end_date)
            gsc_queries = fetch_gsc_query_report(config, start_date, end_date)
        else:
            gsc_daily = pd.DataFrame()
            gsc_queries = pd.DataFrame()
            messages.append("⚠️ 尚未完成 GSC 授權，目前隱藏自然搜尋數據。")

        merged_frame = merge_ga4_and_ads(ga4_frame, ads_frame)
        
        return {
            "mode": "live",
            "messages": messages,
            "ga4": ga4_frame,
            "ads": ads_frame,
            "merged": merged_frame,
            "gsc_daily": gsc_daily,
            "gsc_queries": gsc_queries,
        }
    except Exception as exc:
        if not use_demo:
            raise RuntimeError(f"正式 API 載入失敗：{exc}") from exc

        ga4_frame, ads_frame, merged_frame = build_demo_data(start_date, end_date)
        return {
            "mode": "demo",
            "messages": [
                f"正式 API 載入失敗，已暫時切回示範資料。詳細原因：{exc}"
            ],
            "ga4": ga4_frame,
            "ads": ads_frame,
            "merged": merged_frame,
            "gsc_daily": gsc_daily,
            "gsc_queries": gsc_queries,
        }


def render_header(payload_mode: str) -> None:
    source_label = "正式 API 模式" if payload_mode == "live" else "示範資料模式"
    st.markdown(
        """
        <div class="hero-card">
          <div class="hero-kicker">本機分析工作室</div>
          <h1>GA4 與 Google Ads 數據分析儀表板</h1>
          <p class="hero-copy">
            在同一個畫面比較流量、廣告花費、轉換與營收，並用日期加上廣告活動身分做資料對齊。
            如果您還沒補齊憑證，可以先到「設定精靈」登入 Google 帳號或直接把設定值寫入 `.env`。
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        f"資料來源：{source_label} | 合併邏輯：日期 + 廣告活動 ID，"
        "若缺值則退回活動名稱"
    )


def render_sidebar(
    config: AppConfig,
    theme_type: str,
) -> tuple[date, date, int, bool, bool]:
    with st.sidebar:
        st.markdown("## 儀表板篩選")
        with st.form("dashboard_controls"):
            start_date = st.date_input(
                "開始日期",
                value=st.session_state["start_date"],
            )
            end_date = st.date_input(
                "結束日期",
                value=st.session_state["end_date"],
            )
            top_n = st.slider(
                "熱門活動數量",
                min_value=5,
                max_value=20,
                value=st.session_state["top_n"],
            )
            use_demo = st.checkbox(
                "當正式 API 無法使用時，自動切回示範資料",
                value=st.session_state["use_demo"],
            )
            submitted = st.form_submit_button(
                "重新載入資料",
                use_container_width=True,
            )

        st.markdown("## 憑證狀態")
        if config.ga4_ready:
            st.success("GA4 已就緒")
        else:
            st.warning("GA4 資源 ID 或服務帳戶 JSON 尚未完成")

        if config.google_ads_ready:
            st.success("Google Ads 已就緒")
        else:
            st.warning("Google Ads 客戶 ID / 開發人員權杖 / 授權尚未完成")

        if config.gsc_ready:
            st.success("GSC 已就緒")
        else:
            st.warning("GSC 網址 / 授權尚未完成")

        st.markdown("## 系統外觀")
        st.caption(f"目前偵測到的版面主題：`{'深色' if theme_type == 'dark' else '淺色'}`")

        
        st.markdown("## 網域分析切換")
        sites = load_sites()
        domain_options = ["全部網域 (All)"] + [s.domain_name for s in sites]
        selected_domain = st.selectbox("選擇要獨立檢視的網站", domain_options, key="domain_filter")
        
        st.markdown("## 目前對齊維度")
        st.caption(
            f"GA4：`{config.ga4_campaign_id_dimension}` + "
            f"`{config.ga4_campaign_dimension}`"
        )
        st.caption(
            "主要比較指標：Ads 點擊、花費、轉換，與 GA4 工作階段、關鍵事件、營收"
        )

        if config.google_ads_oauth_client_json_path:
            st.caption(
                "OAuth 用戶端 JSON："
                f"`{config.google_ads_oauth_client_json_path}`"
            )

    return start_date, end_date, top_n, use_demo, submitted


def render_metrics(summary: dict[str, float]) -> None:
    row_a = st.columns(3)
    row_b = st.columns(3)

    row_a[0].metric("Ads 點擊", format_number(summary["ads_clicks"]))
    row_a[1].metric("GA4 工作階段", format_number(summary["ga4_sessions"]))
    row_a[2].metric("Ads 花費", format_number(summary["ads_cost"], 2))

    row_b[0].metric("Ads 轉換", format_number(summary["ads_conversions"], 2))
    row_b[1].metric("GA4 營收", format_number(summary["ga4_total_revenue"], 2))
    row_b[2].metric("Ads ROAS", format_ratio(summary["ads_roas"]))


def render_charts(
    merged_frame: pd.DataFrame,
    top_n: int,
    theme_type: str,
) -> None:
    daily = build_daily_summary(merged_frame)
    campaigns = build_campaign_summary(merged_frame, top_n=top_n)

    trend_columns = st.columns(2)

    gsc_daily = st.session_state["dashboard_payload"].get("gsc_daily", pd.DataFrame())
    if not gsc_daily.empty:
        daily = daily.merge(gsc_daily, on="date", how="left")
        for col in ["gsc_clicks", "gsc_impressions"]:
            daily[col] = pd.to_numeric(daily[col], errors="coerce").fillna(0.0)
            
        METRIC_LABELS.update({"gsc_clicks": "自然搜尋點擊 (GSC)"})
        COLOR_MAP.update({"自然搜尋點擊 (GSC)": "#8b5cf6"})
        value_vars = ["ads_clicks", "ga4_sessions", "ga4_key_events", "gsc_clicks"]
    else:
        value_vars = ["ads_clicks", "ga4_sessions", "ga4_key_events"]

    volume_frame = daily.melt(
        id_vars="date",
        value_vars=[v for v in value_vars if v in daily.columns],
        var_name="metric",
        value_name="value",
    )
    volume_frame["metric"] = volume_frame["metric"].map(METRIC_LABELS)
    volume_chart = px.line(
        volume_frame,
        x="date",
        y="value",
        color="metric",
        markers=True,
        color_discrete_map=COLOR_MAP,
    )
    trend_columns[0].plotly_chart(
        style_figure(volume_chart, "每日流量與關鍵事件趨勢", theme_type),
        use_container_width=True,
    )

    value_frame = daily.melt(
        id_vars="date",
        value_vars=["ads_cost", "ga4_total_revenue"],
        var_name="metric",
        value_name="value",
    )
    value_frame["metric"] = value_frame["metric"].map(METRIC_LABELS)
    value_chart = px.line(
        value_frame,
        x="date",
        y="value",
        color="metric",
        markers=True,
        color_discrete_map=COLOR_MAP,
    )
    trend_columns[1].plotly_chart(
        style_figure(value_chart, "每日花費與營收趨勢", theme_type),
        use_container_width=True,
    )

    campaign_columns = st.columns(2)

    value_compare = campaigns[["campaign_name", "ads_cost", "ga4_total_revenue"]].melt(
        id_vars="campaign_name",
        value_vars=["ads_cost", "ga4_total_revenue"],
        var_name="metric",
        value_name="value",
    )
    value_compare["metric"] = value_compare["metric"].map(METRIC_LABELS)
    value_compare_chart = px.bar(
        value_compare,
        x="value",
        y="campaign_name",
        color="metric",
        orientation="h",
        barmode="group",
        color_discrete_map=COLOR_MAP,
    )
    campaign_columns[0].plotly_chart(
        style_figure(value_compare_chart, "熱門活動的花費與營收比較", theme_type),
        use_container_width=True,
    )

    performance_chart = px.bar(
        campaigns.sort_values("ads_roas", ascending=True),
        x="ads_roas",
        y="campaign_name",
        orientation="h",
        color="session_to_click_ratio",
        color_continuous_scale=[
            [0.0, "#f59e0b"],
            [0.5, "#14b8a6"],
            [1.0, "#38bdf8"],
        ],
        labels={
            "ads_roas": "Ads ROAS",
            "campaign_name": "廣告活動",
            "session_to_click_ratio": "工作階段 / 點擊",
        },
    )
    campaign_columns[1].plotly_chart(
        style_figure(performance_chart, "活動效率快照", theme_type),
        use_container_width=True,
    )


def render_portfolio_summary(payload: dict[str, pd.DataFrame]) -> None:
    st.markdown("## 🌐 網站組合總覽 (Portfolio Performance)")
    
    ga4 = payload.get("ga4", pd.DataFrame())
    gsc = payload.get("gsc_daily", pd.DataFrame())
    
    if ga4.empty and gsc.empty:
        st.info("尚無實例數據可供分網域彙整。")
        return
        
    # Aggregate GA4 by domain
    ga4_agg = pd.DataFrame()
    if not ga4.empty and "domain" in ga4.columns:
        ga4_agg = ga4.groupby("domain").agg({
            "ga4_sessions": "sum",
            "ga4_key_events": "sum",
            "ga4_total_revenue": "sum"
        }).reset_index()
    
    # Aggregate GSC by domain
    gsc_agg = pd.DataFrame()
    if not gsc.empty and "domain" in gsc.columns:
        gsc_agg = gsc.groupby("domain").agg({
            "gsc_clicks": "sum",
            "gsc_impressions": "sum",
            "gsc_position": "mean"
        }).reset_index()
        
    # Merge summary
    if not ga4_agg.empty and not gsc_agg.empty:
        summary = ga4_agg.merge(gsc_agg, on="domain", how="outer").fillna(0)
    elif not ga4_agg.empty:
        summary = ga4_agg
    elif not gsc_agg.empty:
        summary = gsc_agg
    else:
        st.info("資料中缺少 domain 維度。")
        return

    # Rename for display
    display_summary = summary.rename(columns={
        "domain": "網域名稱",
        "ga4_sessions": "工作階段 (GA4)",
        "ga4_key_events": "關鍵事件 (GA4)",
        "ga4_total_revenue": "營收 (GA4)",
        "gsc_clicks": "自然點擊 (GSC)",
        "gsc_impressions": "自然曝光 (GSC)",
        "gsc_position": "平均排名 (GSC)"
    })
    
    # Format
    if "平均排名 (GSC)" in display_summary.columns:
        display_summary["平均排名 (GSC)"] = display_summary["平均排名 (GSC)"].round(1)
    if "營收 (GA4)" in display_summary.columns:
        display_summary["營收 (GA4)"] = display_summary["營收 (GA4)"].map(lambda x: f"${x:,.0f}")
        
    st.dataframe(display_summary, use_container_width=True, hide_index=True)


def render_table(merged_frame: pd.DataFrame, top_n: int) -> None:
    campaign_table = build_campaign_summary(merged_frame, top_n=top_n).copy()
    if campaign_table.empty:
        st.info("目前選取的日期區間沒有任何資料列。")
        return

    campaign_table = campaign_table.rename(
        columns={
            "campaign_id": "活動 ID",
            "campaign_name": "廣告活動",
            "ads_impressions": "Ads 曝光",
            "ads_clicks": "Ads 點擊",
            "ads_cost": "Ads 花費",
            "ads_conversions": "Ads 轉換",
            "ads_conversions_value": "Ads 轉換價值",
            "ga4_sessions": "GA4 工作階段",
            "ga4_key_events": "GA4 關鍵事件",
            "ga4_total_revenue": "GA4 營收",
            "ads_roas": "Ads ROAS",
            "ads_cpa": "Ads CPA",
            "session_to_click_ratio": "工作階段 / 點擊",
        }
    )

    for column in [
        "Ads 花費",
        "Ads 轉換",
        "Ads 轉換價值",
        "GA4 營收",
        "Ads ROAS",
        "Ads CPA",
        "工作階段 / 點擊",
    ]:
        campaign_table[column] = campaign_table[column].round(2)

    st.markdown("## 活動明細表")
    st.dataframe(campaign_table, use_container_width=True, hide_index=True)

    csv_bytes = merged_frame.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "下載合併後 CSV",
        data=csv_bytes,
        file_name="ga4_google_ads_dashboard.csv",
        mime="text/csv",
        use_container_width=False,
    )


def render_setup_status(config: AppConfig) -> None:
    status_columns = st.columns(4)
    status_columns[0].metric(
        "GA4 資源 ID",
        "已設定" if config.ga4_property_id else "未設定",
    )
    status_columns[1].metric(
        "GA4 服務帳戶 JSON",
        "已找到" if config.effective_ga4_credentials_path else "未找到",
    )
    status_columns[2].metric(
        "Ads 開發人員權杖",
        "已設定" if config.google_ads_developer_token else "未設定",
    )
    status_columns[3].metric(
        "Ads 更新權杖",
        "已設定" if config.google_ads_refresh_token else "未設定",
    )


def render_setup_guidance() -> None:
    st.markdown("### 哪些值可以自動取得？")
    st.markdown(
        """
- `GA4 資源 ID`：可以直接用 Google 登入後自動列出可存取的資源
- `Google Ads 更新權杖`：可以直接在這個本機應用程式中登入 Google 取得
- `Google Ads 客戶 ID`：若已有開發人員權杖 + 更新權杖，可自動列出可存取的帳戶 ID
- `Google Ads 開發人員權杖`：無法透過 OAuth 自動產生，必須到 Google Ads API 中心申請
"""
    )


def render_upload_section(config: AppConfig) -> None:
    st.markdown("### 上傳憑證檔")
    upload_columns = st.columns(2)

    with upload_columns[0]:
        ga4_json = st.file_uploader(
            "上傳 GA4 服務帳戶 JSON",
            type=["json"],
            key="ga4_service_account_upload",
        )
        if st.button("儲存 GA4 服務帳戶 JSON", use_container_width=True):
            if not ga4_json:
                st.warning("請先選擇 GA4 服務帳戶 JSON。")
            else:
                destination = BASE_DIR / "credentials" / "ga4-service-account.json"
                save_bytes_file(ga4_json.getvalue(), destination)
                update_env_values(
                    {"GA4_CREDENTIALS_PATH": to_project_relative(destination)}
                )
                st.success(f"已儲存至 {destination}")
                st.rerun()

        if config.effective_ga4_credentials_path:
            st.caption(f"目前 GA4 JSON：`{config.effective_ga4_credentials_path}`")

    with upload_columns[1]:
        ads_json = st.file_uploader(
            "上傳 Google Ads OAuth 用戶端 JSON",
            type=["json"],
            key="ads_oauth_upload",
        )
        if st.button("儲存 Google Ads OAuth JSON", use_container_width=True):
            if not ads_json:
                st.warning("請先選擇 Google Ads OAuth 用戶端 JSON。")
            else:
                destination = BASE_DIR / "credentials" / "google-ads-oauth-client.json"
                save_bytes_file(ads_json.getvalue(), destination)
                update_env_values(
                    {"GOOGLE_ADS_OAUTH_CLIENT_JSON_PATH": to_project_relative(destination)}
                )
                st.success(f"已儲存至 {destination}")
                st.rerun()

        if config.google_ads_oauth_client_json_path:
            st.caption(
                "目前 Ads OAuth JSON："
                f"`{config.google_ads_oauth_client_json_path}`"
            )


def render_auto_fetch_section(config: AppConfig) -> None:
    st.markdown("### 🚀 一鍵綜合登入 (自動獲取 API 授權與清單)")
    st.caption("您可以根據需求選擇僅登入 GA4、僅登入 Google Ads，或者綜合授權兩者。完成後會自動儲存更新權杖，並列出可用的 GA4 資源供您選擇綁定。")

    if not config.google_ads_oauth_client_json_path:
        st.warning("請先在上方的「上傳憑證檔」區塊設定 Google OAuth 用戶端 JSON。")
        return

    buttons_col1, buttons_col2, buttons_col3 = st.columns(3)
    
    with buttons_col1:
        clicked_ga4 = st.button("僅登入獲取 GA4", use_container_width=True)
    with buttons_col2:
        clicked_ads = st.button("僅登入獲取 Ads", use_container_width=True)
    with buttons_col3:
        clicked_both = st.button("一鍵綜合登入 (兩者)", use_container_width=True, type="primary")
        
    mode = None
    if clicked_ga4: mode = "ga4"
    elif clicked_ads: mode = "ads"
    elif clicked_both: mode = "both"

    if mode:
        try:
            with st.spinner("正在開啟 Google 登入視窗，請在瀏覽器中完成授權..."):
                result = unified_google_login_and_fetch(config.google_ads_oauth_client_json_path, mode=mode)
            
            if result["refresh_token"]:
                update_env_values({"GOOGLE_ADS_REFRESH_TOKEN": str(result["refresh_token"])})
                st.session_state["generated_refresh_token"] = result["refresh_token"]
            
            if mode in ("ga4", "both", "all"):
                st.session_state["ga4_property_choices"] = result.get("ga4_properties", [])
            if mode in ("gsc", "both", "all"):
                st.session_state["gsc_sites"] = result.get("gsc_sites", [])
                
            st.success("登入成功！更新權杖已自動存入 `.env`。")
            st.rerun()
        except Exception as exc:
            st.error(f"登入失敗：{exc}")

    # --- Site Portfolio Manager ---
    st.markdown("---")
    st.markdown("### 🌐 多網域/網站組合管理 (Site Manager)")
    st.info("在此您可以建立並綁定多個網站。系統會自動抓取所有綁定網站的資料，讓您能在儀表板中同時查看。")

    existing_sites = load_sites()
    if existing_sites:
        site_data = []
        for s in existing_sites:
            site_data.append({
                "網站名稱": s.domain_name,
                "GA4 ID": s.ga4_property_id,
                "GSC 網址": s.gsc_site_url
            })
        st.dataframe(pd.DataFrame(site_data), use_container_width=True, hide_index=True)
        
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            del_site_val = st.selectbox("選擇要移除的網站", [s.domain_name for s in existing_sites], key="del_site_select")
        with del_col2:
            st.write("")
            if st.button("🗑️ 移除網站", use_container_width=True):
                remove_site(del_site_val)
                st.success(f"已移除網站: {del_site_val}")
                st.rerun()

    st.markdown("#### ➕ 新增網站至組合")
    with st.container(border=True):
        col_new1, col_new2 = st.columns(2)
        with col_new1:
            new_domain = st.text_input("自訂網站名稱 (例如: 品牌官網)", placeholder="請輸入易辨識的名稱")
        
        ga4_choices = st.session_state.get("ga4_property_choices", [])
        gsc_choices = st.session_state.get("gsc_sites", [])
        
        if ga4_choices and gsc_choices:
            with col_new2:
                ga4_labels = [f"{item['account_display_name']} > {item['property_display_name']} ({item['property_id']})" for item in ga4_choices]
                selected_ga4_label = st.selectbox("選擇 GA4 資源", ga4_labels)
                selected_ga4_idx = ga4_labels.index(selected_ga4_label)
                new_ga4_id = ga4_choices[selected_ga4_idx]["property_id"]
                
            new_gsc_url = st.selectbox("選擇對應的 GSC 資源網址", gsc_choices)
            
            if st.button("✨ 儲存並加入網站組合 (Add Site)", type="primary", use_container_width=True):
                if new_domain:
                    add_site(new_domain, new_ga4_id, new_gsc_url)
                    st.success(f"與網域 [{new_domain}] 綁定成功！")
                    st.rerun()
                else:
                    st.error("請填寫網站名稱！")
        else:
            st.warning("請先使用上方的登入按鈕完成授權，系統才能列出您的 GA4 與 GSC 資源供您選擇。")

    # Keep refresh token view
    generated_refresh_token = st.session_state.get("generated_refresh_token", "")
    if generated_refresh_token:
        with st.expander("檢視目前 OAuth 更新權杖 (Refresh Token)", expanded=False):
            st.code(generated_refresh_token)
            st.caption("此權杖已自動同步至 .env 檔案中。")


def render_ads_customer_section(config: AppConfig) -> None:
    st.markdown("### 讀取可存取的 Google Ads 客戶 ID")
    st.caption(
        "這一步需要您已具備 開發人員權杖與更新權杖。若已完成，"
        "可以直接列出當前 OAuth 帳號可存取的 Google Ads 客戶 ID。"
    )

    if not config.google_ads_developer_token:
        st.info("尚未設定開發人員權杖，因此目前無法自動列出客戶 ID。")
        return

    if not config.google_ads_refresh_token:
        st.info("尚未取得更新權杖，因此目前無法自動列出客戶 ID。")
        return

    if st.button("列出我的 Google Ads 客戶 ID", use_container_width=False):
        try:
            with st.spinner("正在讀取 Google Ads 可存取帳戶..."):
                customers = list_accessible_google_ads_customers(config)
            st.session_state["ads_customer_choices"] = customers
            if customers:
                st.success(f"共找到 {len(customers)} 個可存取的 Google Ads 客戶 ID。")
            else:
                st.warning("沒有讀取到任何可存取的 客戶 ID。")
        except Exception as exc:
            st.error(f"讀取 Google Ads 客戶 ID 失敗：{exc}")

    customer_choices = st.session_state.get("ads_customer_choices", [])
    if customer_choices:
        selected_customer = st.selectbox(
            "選擇要寫入的 Google Ads 客戶 ID",
            customer_choices,
            key="selected_ads_customer_id",
        )
        if st.button("寫入 GOOGLE_ADS_CUSTOMER_ID"):
            update_env_values({"GOOGLE_ADS_CUSTOMER_ID": selected_customer})
            st.success(f"已寫入 GOOGLE_ADS_CUSTOMER_ID={selected_customer}")
            st.rerun()

        st.dataframe(
            pd.DataFrame({"可存取的客戶 ID": customer_choices}),
            use_container_width=True,
            hide_index=True,
        )


def render_manual_help_section() -> None:
    st.markdown("### 仍需手動取得的值")
    help_columns = st.columns(2)

    with help_columns[0]:
        st.markdown(
            """
<div class="setup-card">
  <h4>Google Ads 開發人員權杖</h4>
  <p class="setup-note">
    這個值無法透過 OAuth 自動產生。請登入 Google Ads 後，前往 API Center 申請。
    測試帳號通常會先拿到測試版 token，正式上線前再申請升級。
  </p>
</div>
""",
            unsafe_allow_html=True,
        )
        st.link_button("前往 Google Ads API Center", "https://ads.google.com/aw/apicenter")

    with help_columns[1]:
        st.markdown(
            """
<div class="setup-card">
  <h4>Google Ads 客戶 ID</h4>
  <p class="setup-note">
    可在 Google Ads 畫面右上角找到，格式通常像是 123-456-7890。
    如果您使用 MCC，`Login Customer ID` 通常填管理帳戶 ID。
  </p>
</div>
""",
            unsafe_allow_html=True,
        )
        st.link_button("前往 Google Ads 首頁", "https://ads.google.com/")


def render_env_form(config: AppConfig) -> None:
    st.markdown("### 直接寫入設定值")
    with st.form("env_settings_form"):
        ga4_property_id = st.text_input(
            "GA4 資源 ID",
            value=config.ga4_property_id or "",
            help="只填數字，例如 123456789，不需要加上 properties/。",
        )
        ga4_credentials_path = st.text_input(
            "GA4 服務帳戶 JSON 路徑",
            value=str(config.ga4_credentials_path or ""),
        )
        google_ads_customer_id = st.text_input(
            "Google Ads 客戶 ID",
            value=config.google_ads_customer_id or "",
        )
        google_ads_login_customer_id = st.text_input(
            "Google Ads 登入客戶 ID (我的客戶中心才需要)",
            value=config.google_ads_login_customer_id or "",
        )
        google_ads_developer_token = st.text_input(
            "Google Ads 開發人員權杖",
            value=config.google_ads_developer_token or "",
        )
        google_ads_oauth_client_json_path = st.text_input(
            "Google Ads OAuth 用戶端 JSON 路徑",
            value=str(config.google_ads_oauth_client_json_path or ""),
        )
        google_ads_refresh_token = st.text_input(
            "Google Ads 更新權杖",
            value=config.google_ads_refresh_token or "",
            type="password",
        )
        submitted = st.form_submit_button("儲存到 .env", use_container_width=True)

    if submitted:
        update_env_values(
            {
                "GA4_PROPERTY_ID": ga4_property_id,
                "GA4_CREDENTIALS_PATH": ga4_credentials_path,
                "GOOGLE_ADS_CUSTOMER_ID": google_ads_customer_id,
                "GOOGLE_ADS_LOGIN_CUSTOMER_ID": google_ads_login_customer_id,
                "GOOGLE_ADS_DEVELOPER_TOKEN": google_ads_developer_token,
                "GOOGLE_ADS_OAUTH_CLIENT_JSON_PATH": google_ads_oauth_client_json_path,
                "GOOGLE_ADS_REFRESH_TOKEN": google_ads_refresh_token,
            }
        )
        st.success("已將設定值寫入 `.env`。")
        st.rerun()


def render_setup_wizard(config: AppConfig) -> None:
    st.markdown("## 設定精靈")
    st.caption(
        "這裡可以幫您補齊 GA4 與 Google Ads 所需設定。能自動取得的值會直接透過 Google 登入完成；"
        "無法自動取得的值，則提供最短路徑與直接寫入 `.env` 的表單。"
    )

    render_setup_status(config)
    render_setup_guidance()
    render_upload_section(config)
    render_auto_fetch_section(config)
    render_ads_customer_section(config)
    render_manual_help_section()
    render_env_form(config)


def _check_password() -> None:
    """若有設定 VIEWER_PASSWORD，則顯示密碼登入頁面。"""
    import os

    required_pw = None
    try:
        required_pw = st.secrets.get("VIEWER_PASSWORD", None)
    except Exception:
        pass
    if required_pw is None:
        required_pw = os.environ.get("VIEWER_PASSWORD", None)

    if not required_pw:
        return  # 未設定密碼，直接開放

    if st.session_state.get("_viewer_authenticated"):
        return

    st.set_page_config(page_title="GA4 儀表板 — 登入", layout="centered")
    st.markdown(
        """
        <style>
        .login-box { max-width: 400px; margin: 6rem auto; text-align: center; }
        </style>
        <div class="login-box">
        """,
        unsafe_allow_html=True,
    )
    st.markdown("## 🔐 請輸入查看密碼")
    pw_input = st.text_input("密碼", type="password", key="_pw_field")
    if st.button("登入", use_container_width=True):
        if pw_input == required_pw:
            st.session_state["_viewer_authenticated"] = True
            st.rerun()
        else:
            st.error("密碼錯誤，請重新輸入。")
    st.stop()


def main() -> None:
    _check_password()
    config = load_config()
    initialize_state(config)
    theme_type = get_theme_type()
    st.markdown(build_theme_css(theme_type), unsafe_allow_html=True)

    start_date, end_date, top_n, use_demo, submitted = render_sidebar(
        config,
        theme_type,
    )

    if start_date > end_date:
        st.error("開始日期不能晚於結束日期。")
        st.stop()

    should_reload = submitted or "dashboard_payload" not in st.session_state
    if should_reload:
        st.session_state["start_date"] = start_date
        st.session_state["end_date"] = end_date
        st.session_state["top_n"] = top_n
        st.session_state["use_demo"] = use_demo

        try:
            with st.spinner("正在載入儀表板資料..."):
                sites = load_sites()
                st.session_state["dashboard_payload"] = load_dashboard_data(
                    config=config,
                    sites=sites,
                    start_date=start_date,
                    end_date=end_date,
                    use_demo=use_demo,
                )
                st.session_state["dashboard_error"] = ""
        except Exception as exc:
            st.session_state["dashboard_error"] = str(exc)

    payload = st.session_state.get("dashboard_payload", {})
    render_header(payload.get("mode", "demo"))

    dashboard_tab, setup_tab = st.tabs(["儀表板總覽", "設定精靈"])

    with dashboard_tab:
        dashboard_error = st.session_state.get("dashboard_error", "")
        if dashboard_error:
            st.error(dashboard_error)
            st.info("請切換到「設定精靈」分頁補齊憑證設定。")

        elif not payload:
            st.info("請先從左側載入資料。")

        else:
            sel_domain = st.session_state.get("domain_filter", "全部網域 (All)")
            if sel_domain != "全部網域 (All)":
                import copy
                payload = copy.copy(payload)
                if "domain" in payload["ga4"].columns and not payload["ga4"].empty:
                    payload["ga4"] = payload["ga4"][payload["ga4"]["domain"] == sel_domain]
                if "domain" in payload["gsc_daily"].columns and not payload["gsc_daily"].empty:
                    payload["gsc_daily"] = payload["gsc_daily"][payload["gsc_daily"]["domain"] == sel_domain]
                if "domain" in payload["gsc_queries"].columns and not payload["gsc_queries"].empty:
                    payload["gsc_queries"] = payload["gsc_queries"][payload["gsc_queries"]["domain"] == sel_domain]
                from data_processor import merge_ga4_and_ads
                payload["merged"] = merge_ga4_and_ads(payload["ga4"], payload["ads"])

            for message in payload["messages"]:
                if payload["mode"] == "demo":
                    st.info(message)
                else:
                    st.warning(message)

            merged_frame = payload["merged"]
            summary = summarize_dashboard(merged_frame)

            render_metrics(summary)

            if sel_domain == "全部網域 (All)":
                render_portfolio_summary(payload)

            render_charts(merged_frame, top_n=top_n, theme_type=theme_type)
            render_table(merged_frame, top_n=top_n)

            if "gsc_queries" in payload and not payload["gsc_queries"].empty:
                st.markdown("## 自然搜尋排名 (GSC Top Queries)")
                gsc_q = payload["gsc_queries"].rename(columns={
                    "query": "搜尋字詞",
                    "gsc_clicks": "自然搜尋點擊",
                    "gsc_impressions": "曝光次數",
                    "gsc_ctr": "點擊率 (CTR)",
                    "gsc_position": "平均排名"
                })
                gsc_q["點擊率 (CTR)"] = (gsc_q["點擊率 (CTR)"] * 100).round(2).astype(str) + "%"
                gsc_q["平均排名"] = gsc_q["平均排名"].round(1)
                st.dataframe(gsc_q, use_container_width=True, hide_index=True)

            with st.expander("檢視原始 API 資料表", expanded=False):
                raw_columns = st.columns(3)
                raw_columns[0].markdown("### GA4")
                raw_columns[0].dataframe(payload["ga4"], use_container_width=True)
                raw_columns[1].markdown("### Google Ads")
                raw_columns[1].dataframe(payload["ads"], use_container_width=True)
                raw_columns[2].markdown("### Google Search Console")
                raw_columns[2].dataframe(payload.get("gsc_daily", pd.DataFrame()), use_container_width=True)

    with setup_tab:
        render_setup_wizard(config)


if __name__ == "__main__":
    main()
