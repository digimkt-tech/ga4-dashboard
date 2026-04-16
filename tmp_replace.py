import pathlib

app_path = pathlib.Path(r"c:\Users\digimkt\Downloads\GA4與ads\app.py")
content = app_path.read_text(encoding="utf-8")

replacements = {
    "Local Analytics Studio": "本機分析工作室",
    "GA4 Property ID 或服務帳戶 JSON 尚未完成": "GA4 資源 ID 或服務帳戶 JSON 尚未完成",
    "Google Ads Customer ID / Developer Token / 授權尚未完成": "Google Ads 客戶 ID / 開發人員權杖 / 授權尚未完成",
    '"GA4 Property ID"': '"GA4 資源 ID"',
    '"GA4 JSON"': '"GA4 服務帳戶 JSON"',
    '"Ads Developer Token"': '"Ads 開發人員權杖"',
    '"Ads Refresh Token"': '"Ads 更新權杖"',
    '- `GA4 Property ID`：可以直接用 Google 登入後自動列出可存取的屬性': '- `GA4 資源 ID`：可以直接用 Google 登入後自動列出可存取的資源',
    '- `Google Ads Refresh Token`：可以直接在這個本機 app 中登入 Google 取得': '- `Google Ads 更新權杖`：可以直接在這個本機應用程式中登入 Google 取得',
    '- `Google Ads Customer ID`：若已有 Developer Token + Refresh Token，可自動列出可存取的帳戶 ID': '- `Google Ads 客戶 ID`：若已有開發人員權杖 + 更新權杖，可自動列出可存取的帳戶 ID',
    '- `Google Ads Developer Token`：無法透過 OAuth 自動產生，必須到 Google Ads API Center 申請': '- `Google Ads 開發人員權杖`：無法透過 OAuth 自動產生，必須到 Google Ads API 中心申請',
    '"### 直接登入取得 GA4 Property ID"': '"### 直接登入取得 GA4 資源 ID"',
    '自動列出您可存取的 GA4 屬性。': '自動列出您可存取的 GA4 資源。',
    '"登入 Google 並列出 GA4 Property"': '"登入 Google 並列出 GA4 資源"',
    '讀取 GA4 屬性...': '讀取 GA4 資源...',
    '個 GA4 Property。': '個 GA4 資源。',
    '可讀取的 GA4 Property。': '可讀取的 GA4 資源。',
    '讀取 GA4 Property 失敗：': '讀取 GA4 資源失敗：',
    '"property_display_name": "Property 名稱",': '"property_display_name": "資源名稱",',
    '"property_id": "Property ID",': '"property_id": "資源 ID",',
    '"選擇要寫入的 GA4 Property"': '"選擇要寫入的 GA4 資源"',
    '"Property 名稱", "Property ID",': '"資源名稱", "資源 ID",',
    '"### 直接登入取得 Google Ads Refresh Token"': '"### 直接登入取得 Google Ads 更新權杖"',
    '把 Refresh Token 寫進': '把更新權杖寫進',
    '"登入 Google 並取得 Refresh Token"': '"登入 Google 並取得更新權杖"',
    'Refresh Token 已取得': '更新權杖已取得',
    '取得 Refresh Token 失敗：': '取得更新權杖失敗：',
    '"檢視剛取得的 Refresh Token"': '"檢視剛取得的更新權杖"',
    '"### 讀取可存取的 Google Ads Customer ID"': '"### 讀取可存取的 Google Ads 客戶 ID"',
    'Developer Token 與 Refresh Token。': '開發人員權杖與更新權杖。',
    'Google Ads Customer ID。"': 'Google Ads 客戶 ID。"',
    '設定 Developer Token，': '設定開發人員權杖，',
    '列出 Customer ID。': '列出客戶 ID。',
    '取得 Refresh Token，': '取得更新權杖，',
    '"列出我的 Google Ads Customer ID"': '"列出我的 Google Ads 客戶 ID"',
    'Google Ads Customer ID。': 'Google Ads 客戶 ID。',
    'Customer ID。"': '客戶 ID。"',
    '讀取 Google Ads Customer ID 失敗：': '讀取 Google Ads 客戶 ID 失敗：',
    '"選擇要寫入的 Google Ads Customer ID"': '"選擇要寫入的 Google Ads 客戶 ID"',
    '"可存取的 Customer ID"': '"可存取的客戶 ID"',
    '<h4>Google Ads Developer Token</h4>': '<h4>Google Ads 開發人員權杖</h4>',
    '<h4>Google Ads Customer ID</h4>': '<h4>Google Ads 客戶 ID</h4>',
    '"Google Ads Customer ID",': '"Google Ads 客戶 ID",',
    '"Google Ads Login Customer ID（MCC 才需要）",': '"Google Ads 登入客戶 ID (我的客戶中心才需要)",',
    '"Google Ads Developer Token",': '"Google Ads 開發人員權杖",',
    '"Google Ads Refresh Token",': '"Google Ads 更新權杖",',
}

for old, new in replacements.items():
    content = content.replace(old, new)

app_path.write_text(content, encoding="utf-8")
print("Done")
