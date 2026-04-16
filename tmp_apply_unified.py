import pathlib
import sys

base = pathlib.Path(r"c:\Users\digimkt\Downloads\GA4與ads")

# 1. Modify setup_helpers.py
setup_path = base / "setup_helpers.py"
setup_code = setup_path.read_text(encoding="utf-8")

if "unified_google_login_and_fetch" not in setup_code:
    new_func = """
def unified_google_login_and_fetch(client_json_path: Path) -> dict[str, object]:
    credentials = run_local_google_login(
        client_json_path=client_json_path,
        scopes=[GA4_READONLY_SCOPE, GOOGLE_ADS_SCOPE],
        authorization_prompt_message=(
            "請在瀏覽器中登入 Google 帳號並一同授權 Google Ads 與 GA4 讀取權限：\\n{url}"
        ),
        success_message="綜合授權完成，請回到應用程式。",
    )
    if not credentials.valid:
        credentials.refresh(Request())

    refresh_token = credentials.refresh_token or ""

    url = "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"
    headers = {"Authorization": f"Bearer {credentials.token}"}
    properties: list[dict[str, str]] = []
    page_token = ""

    while True:
        params = {"pageSize": 200}
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            payload = response.json()
            for account_summary in payload.get("accountSummaries", []):
                account_name = account_summary.get("displayName", "")
                for property_summary in account_summary.get("propertySummaries", []):
                    property_resource = property_summary.get("property", "")
                    properties.append(
                        {
                            "account_display_name": account_name,
                            "property_display_name": property_summary.get("displayName", ""),
                            "property_id": property_resource.split("/")[-1] if property_resource else "",
                            "property_type": property_summary.get("propertyType", ""),
                        }
                    )

            page_token = payload.get("nextPageToken", "")
            if not page_token:
                break
        else:
            break

    properties.sort(
        key=lambda item: (
            item["account_display_name"].lower(),
            item["property_display_name"].lower(),
        )
    )
    return {
        "refresh_token": refresh_token,
        "ga4_properties": properties
    }
"""
    setup_code = setup_code + new_func
    setup_path.write_text(setup_code, encoding="utf-8")


# 2. Modify config.py
config_path = base / "config.py"
config_code = config_path.read_text(encoding="utf-8")

old_ga4_ready = """    @property
    def ga4_ready(self) -> bool:
        return bool(self.ga4_property_id and self.effective_ga4_credentials_path)"""
new_ga4_ready = """    @property
    def ga4_ready(self) -> bool:
        has_credentials = bool(self.effective_ga4_credentials_path)
        has_oauth = bool(self.google_ads_client_id and self.google_ads_client_secret and self.google_ads_refresh_token)
        return bool(self.ga4_property_id and (has_credentials or has_oauth))"""
config_code = config_code.replace(old_ga4_ready, new_ga4_ready)
config_path.write_text(config_code, encoding="utf-8")


# 3. Modify ga4_client.py
ga4_path = base / "ga4_client.py"
ga4_code = ga4_path.read_text(encoding="utf-8")

old_build_client = """def _build_client(config: AppConfig) -> BetaAnalyticsDataClient:
    credentials_path = config.effective_ga4_credentials_path
    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            str(credentials_path),
            scopes=GA4_SCOPES,
        )
        return BetaAnalyticsDataClient(credentials=credentials)

    return BetaAnalyticsDataClient()"""

new_build_client = """def _build_client(config: AppConfig) -> BetaAnalyticsDataClient:
    credentials_path = config.effective_ga4_credentials_path
    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            str(credentials_path),
            scopes=GA4_SCOPES,
        )
        return BetaAnalyticsDataClient(credentials=credentials)

    if config.google_ads_refresh_token and config.google_ads_client_id and config.google_ads_client_secret:
        from google.oauth2.credentials import Credentials
        credentials = Credentials(
            token=None,
            refresh_token=config.google_ads_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config.google_ads_client_id,
            client_secret=config.google_ads_client_secret,
            scopes=GA4_SCOPES,
        )
        return BetaAnalyticsDataClient(credentials=credentials)

    return BetaAnalyticsDataClient()"""

old_ga4_validation = """    if not config.effective_ga4_credentials_path:
        raise ValueError(
            "GA4 credentials are missing. Set GA4_CREDENTIALS_PATH or "
            "GOOGLE_APPLICATION_CREDENTIALS."
        )"""

new_ga4_validation = """    if not config.ga4_ready:
        raise ValueError(
            "GA4 credentials are missing. Use Service Account JSON or User OAuth Refresh Token."
        )"""

ga4_code = ga4_code.replace(old_build_client, new_build_client)
ga4_code = ga4_code.replace(old_ga4_validation, new_ga4_validation)
ga4_path.write_text(ga4_code, encoding="utf-8")

# 4. Modify app.py
app_path = base / "app.py"
app_code = app_path.read_text(encoding="utf-8")

app_code = app_code.replace("from setup_helpers import (", "from setup_helpers import (\\n    unified_google_login_and_fetch,")

old_render_auto_fetch = """def render_auto_fetch_section(config: AppConfig) -> None:
    auto_columns = st.columns(2)

    with auto_columns[0]:
        st.markdown("### 直接登入取得 GA4 資源 ID")
        st.caption(
            "會開啟 Google 登入視窗，完成授權後自動列出您可存取的 GA4 資源。"
        )
        if not config.google_ads_oauth_client_json_path:
            st.warning("請先設定或上傳 Google OAuth 用戶端 JSON。")
        elif st.button("登入 Google 並列出 GA4 資源", use_container_width=True):
            try:
                with st.spinner("正在開啟 Google 登入並讀取 GA4 資源..."):
                    properties = list_ga4_properties_via_google_login(
                        config.google_ads_oauth_client_json_path
                    )
                st.session_state["ga4_property_choices"] = properties
                if properties:
                    st.success(f"已讀取 {len(properties)} 個 GA4 資源。")
                else:
                    st.warning("這個 Google 帳號下目前沒有可讀取的 GA4 資源。")
            except Exception as exc:
                st.error(f"讀取 GA4 資源失敗：{exc}")

        property_choices = st.session_state.get("ga4_property_choices", [])
        if property_choices:
            property_frame = pd.DataFrame(property_choices).rename(
                columns={
                    "account_display_name": "帳戶名稱",
                    "property_display_name": "資源名稱",
                    "property_id": "資源 ID",
                    "property_type": "類型",
                }
            )
            display_labels = [
                f"{item['account_display_name']} / "
                f"{item['property_display_name']} ({item['property_id']})"
                for item in property_choices
            ]
            selected_label = st.selectbox(
                "選擇要寫入的 GA4 資源",
                display_labels,
                key="selected_ga4_property_label",
            )
            selected_index = display_labels.index(selected_label)
            selected_property_id = property_choices[selected_index]["property_id"]

            if st.button("寫入 GA4_PROPERTY_ID", use_container_width=True):
                update_env_values({"GA4_PROPERTY_ID": selected_property_id})
                st.success(f"已寫入 GA4_PROPERTY_ID={selected_property_id}")
                st.rerun()

            st.dataframe(
                property_frame[["帳戶名稱", "資源名稱", "資源 ID", "類型"]],
                use_container_width=True,
                hide_index=True,
            )

    with auto_columns[1]:
        st.markdown("### 直接登入取得 Google Ads 更新權杖")
        st.caption(
            "這個步驟會在本機開啟 Google 授權頁。完成後會自動把更新權杖寫進 `.env`。"
        )
        if not config.google_ads_oauth_client_json_path:
            st.warning("請先設定或上傳 Google OAuth 用戶端 JSON。")
        elif st.button("登入 Google 並取得更新權杖", use_container_width=True):
            try:
                with st.spinner("正在啟動 Google Ads OAuth 授權..."):
                    refresh_token = get_google_ads_refresh_token(
                        config.google_ads_oauth_client_json_path
                    )
                update_env_values({"GOOGLE_ADS_REFRESH_TOKEN": refresh_token})
                st.session_state["generated_refresh_token"] = refresh_token
                st.success("更新權杖已取得，並已自動寫入 `.env`。")
                st.rerun()
            except Exception as exc:
                st.error(f"取得更新權杖失敗：{exc}")

        generated_refresh_token = st.session_state.get("generated_refresh_token", "")
        if generated_refresh_token:
            with st.expander("檢視剛取得的更新權杖", expanded=False):
                st.code(generated_refresh_token)"""

new_render_auto_fetch = """def render_auto_fetch_section(config: AppConfig) -> None:
    st.markdown("### 🚀 一鍵綜合登入 (自動獲取 API 授權與清單)")
    st.caption("透過一次 Google 登入，同時授權 GA4 與 Google Ads。完成後會自動儲存更新權杖，並列出可用的 GA4 資源供您選擇綁定。")

    if not config.google_ads_oauth_client_json_path:
        st.warning("請先在上方的「上傳憑證檔」區塊設定 Google OAuth 用戶端 JSON。")
        return

    if st.button("一鍵登入開啟自動獲取", use_container_width=True, type="primary"):
        try:
            with st.spinner("正在開啟 Google 登入視窗，請在瀏覽器中完成授權..."):
                result = unified_google_login_and_fetch(config.google_ads_oauth_client_json_path)
            
            if result["refresh_token"]:
                update_env_values({"GOOGLE_ADS_REFRESH_TOKEN": str(result["refresh_token"])})
                st.session_state["generated_refresh_token"] = result["refresh_token"]
            
            st.session_state["ga4_property_choices"] = result["ga4_properties"]
            st.success("一鍵登入成功！更新權杖已自動存入 `.env`。如果 GA4 資源清單尚未顯示，請再次確認。")
            st.rerun()
        except Exception as exc:
            st.error(f"綜合登入失敗：{exc}")

    # 以下分為 GA4 資源選擇 與 更新權杖檢視 兩個區塊
    col1, col2 = st.columns(2)
    
    with col1:
        property_choices = st.session_state.get("ga4_property_choices", [])
        if property_choices:
            st.markdown("#### 1. 綁定 GA4 資源")
            property_frame = pd.DataFrame(property_choices).rename(
                columns={
                    "account_display_name": "帳戶名稱",
                    "property_display_name": "資源名稱",
                    "property_id": "資源 ID",
                    "property_type": "類型",
                }
            )
            display_labels = [
                f"{item['account_display_name']} / "
                f"{item['property_display_name']} ({item['property_id']})"
                for item in property_choices
            ]
            selected_label = st.selectbox(
                "選擇要寫入的 GA4 資源",
                display_labels,
                key="selected_ga4_property_label",
            )
            selected_index = display_labels.index(selected_label)
            selected_property_id = property_choices[selected_index]["property_id"]

            if st.button("寫入 GA4_PROPERTY_ID", use_container_width=True):
                update_env_values({"GA4_PROPERTY_ID": selected_property_id})
                st.success(f"已寫入 GA4_PROPERTY_ID={selected_property_id}")
                st.rerun()

            st.dataframe(
                property_frame[["帳戶名稱", "資源名稱", "資源 ID", "類型"]],
                use_container_width=True,
                hide_index=True,
            )
            
    with col2:
        generated_refresh_token = st.session_state.get("generated_refresh_token", "")
        if generated_refresh_token:
            st.markdown("#### 2. 已取得的更新權杖 (已存入 `.env`)")
            with st.expander("檢視更新權杖", expanded=False):
                st.code(generated_refresh_token)"""

app_code = app_code.replace(old_render_auto_fetch, new_render_auto_fetch)

app_path.write_text(app_code, encoding="utf-8")
print("All files patched successfully.")
