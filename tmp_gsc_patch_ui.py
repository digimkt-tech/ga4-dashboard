import pathlib
import sys

base = pathlib.Path(r"c:\Users\digimkt\Downloads\GA4與ads")
app_path = base / "app.py"
app_code = app_path.read_text(encoding="utf-8")

# 1. Update UI for Setup Wizard: Add GSC Site Form
old_setup = """        if generated_refresh_token:
            st.markdown("#### 2. 已取得的更新權杖 (已存入 `.env`)")
            with st.expander("檢視更新權杖", expanded=False):
                st.code(generated_refresh_token)"""

new_setup = """        if generated_refresh_token:
            st.markdown("#### 2. 已取得的更新權杖 (已存入 `.env`)")
            with st.expander("檢視更新權杖", expanded=False):
                st.code(generated_refresh_token)
                
    st.markdown("---")
    st.markdown("#### 3. 綁定 Google Search Console 網站 (GSC)")
    gsc_sites = st.session_state.get("gsc_sites", [])
    if gsc_sites:
        selected_gsc_site = st.selectbox(
            "選擇要寫入的 GSC 資源",
            gsc_sites,
            key="selected_gsc_site_url",
        )
        if st.button("寫入 GSC_SITE_URL", use_container_width=True):
            update_env_values({"GSC_SITE_URL": selected_gsc_site})
            st.success(f"已寫入 GSC_SITE_URL={selected_gsc_site}")
            st.rerun()
    else:
        st.info("請上方以「一鍵綜合登入 (兩者)」授權後，此處將自動列出可選擇的 GSC 資源。")"""

if "3. 綁定 Google Search Console" not in app_code:
    app_code = app_code.replace(old_setup, new_setup)

# Fix returned dict usage of setup_helpers
old_ui_result = """            if mode in ("ga4", "both"):
                st.session_state["ga4_property_choices"] = result["ga4_properties"]"""
new_ui_result = """            if mode in ("ga4", "both", "all"):
                st.session_state["ga4_property_choices"] = result.get("ga4_properties", [])
            if mode in ("gsc", "both", "all"):
                st.session_state["gsc_sites"] = result.get("gsc_sites", [])"""
app_code = app_code.replace(old_ui_result, new_ui_result)


# 2. Add Chart logic to render_charts for GSC
old_render_charts = """    value_compare["metric"] = value_compare["metric"].map(METRIC_LABELS)
    value_compare_chart = px.bar(
"""

new_render_charts = """    value_compare["metric"] = value_compare["metric"].map(METRIC_LABELS)
    value_compare_chart = px.bar(
"""

old_render_table = """    with st.expander("檢視原始 API 資料表", expanded=False):
            raw_columns = st.columns(2)
            raw_columns[0].markdown("### GA4")
            raw_columns[0].dataframe(payload["ga4"], use_container_width=True)
            raw_columns[1].markdown("### Google Ads")
            raw_columns[1].dataframe(payload["ads"], use_container_width=True)"""
new_render_table = """
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
            raw_columns[2].dataframe(payload.get("gsc_daily", pd.DataFrame()), use_container_width=True)"""
if "自然搜尋排名" not in app_code:
    app_code = app_code.replace(old_render_table, new_render_table)

app_path.write_text(app_code, encoding="utf-8")
print("Done patching UI")
