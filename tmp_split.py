import pathlib

base = pathlib.Path(r"c:\Users\digimkt\Downloads\GA4與ads")
setup_path = base / "setup_helpers.py"
setup_code = setup_path.read_text(encoding="utf-8")

old_func = """def unified_google_login_and_fetch(client_json_path: Path) -> dict[str, object]:
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
    }"""

new_func = """def unified_google_login_and_fetch(client_json_path: Path, mode: str = "both") -> dict[str, object]:
    if mode == "ga4":
        scopes = [GA4_READONLY_SCOPE]
        auth_message = "請在瀏覽器中登入 Google 帳號並授權 GA4 讀取權限：\\n{url}"
    elif mode == "ads":
        scopes = [GOOGLE_ADS_SCOPE]
        auth_message = "請在瀏覽器中登入 Google 帳號並授權 Google Ads 操作權限：\\n{url}"
    else:
        scopes = [GA4_READONLY_SCOPE, GOOGLE_ADS_SCOPE]
        auth_message = "請在瀏覽器中登入 Google 帳號並一同授權 Google Ads 與 GA4 權限：\\n{url}"

    credentials = run_local_google_login(
        client_json_path=client_json_path,
        scopes=scopes,
        authorization_prompt_message=auth_message,
        success_message="授權完成，請回到應用程式。",
    )
    if not credentials.valid:
        credentials.refresh(Request())

    refresh_token = credentials.refresh_token or ""
    properties: list[dict[str, str]] = []

    if mode in ("ga4", "both"):
        url = "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"
        headers = {"Authorization": f"Bearer {credentials.token}"}
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
    }"""

setup_code = setup_code.replace(old_func, new_func)
setup_path.write_text(setup_code, encoding="utf-8")

# Modify app.py UI
app_path = base / "app.py"
app_code = app_path.read_text(encoding="utf-8")

old_ui = """    if st.button("一鍵登入開啟自動獲取", use_container_width=True, type="primary"):
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
            st.error(f"綜合登入失敗：{exc}")"""

new_ui = """    buttons_col1, buttons_col2, buttons_col3 = st.columns(3)
    
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
            
            if mode in ("ga4", "both"):
                st.session_state["ga4_property_choices"] = result["ga4_properties"]
                
            st.success("登入成功！更新權杖已自動存入 `.env`。")
            st.rerun()
        except Exception as exc:
            st.error(f"登入失敗：{exc}")"""

app_code = app_code.replace(old_ui, new_ui)

old_text = "透過一次 Google 登入，同時授權 GA4 與 Google Ads。"
new_text = "您可以根據需求選擇僅登入 GA4、僅登入 Google Ads，或者綜合授權兩者。"
app_code = app_code.replace(old_text, new_text)

app_path.write_text(app_code, encoding="utf-8")
print("Split successful")
