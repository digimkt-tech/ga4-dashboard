# GA4 + Google Ads Local Dashboard

This project is a local Streamlit dashboard that pulls data from:

- Google Analytics 4 Data API
- Google Ads API

It cleans and merges campaign performance data, then visualizes the results with Plotly.

## What the app does

- Pulls GA4 campaign data by `date + sessionGoogleAdsCampaignId + sessionGoogleAdsCampaignName`
- Pulls Google Ads campaign data by `segments.date + campaign.id + campaign.name`
- Normalizes campaign names and dates
- Merges GA4 and Google Ads into one analytics table
- Shows KPI cards, time-series charts, campaign comparisons, and a detailed table
- Falls back to demo data when credentials are missing or API calls fail

## Files

- `app.py`: Streamlit dashboard entry point
- `config.py`: environment/config loader
- `ga4_client.py`: GA4 API client
- `ads_client.py`: Google Ads API client
- `data_processor.py`: cleanup, merge, KPI calculations, demo data
- `.env.example`: configuration template
- `google-ads.example.yaml`: Google Ads YAML template

## Setup

1. Install Python 3.10+.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` if needed, then fill in:

- `GA4_PROPERTY_ID`
- `GA4_CREDENTIALS_PATH`
- `GOOGLE_ADS_CUSTOMER_ID`
- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_REFRESH_TOKEN`

5. Choose one Google Ads auth mode:

- Preferred: create `google-ads.yaml`, then point `GOOGLE_ADS_CONFIG_PATH` to it
- Alternative: point `GOOGLE_ADS_OAUTH_CLIENT_JSON_PATH` to the downloaded OAuth client JSON
- Optional override: keep `GOOGLE_ADS_CLIENT_ID` and `GOOGLE_ADS_CLIENT_SECRET` directly in `.env`
- Service account mode is also supported through `GOOGLE_ADS_JSON_KEY_FILE_PATH`

6. If you have the OAuth JSON but not the refresh token yet, generate it with:

```bash
python generate_ads_refresh_token.py
```

7. Run the dashboard:

```bash
streamlit run app.py
```

## Credential checklist

### GA4

- Enable Google Analytics Data API in your Google Cloud project
- Create a service account
- Add the service account email to the GA4 property as a viewer or higher
- Download the JSON key file and set `GA4_CREDENTIALS_PATH`

### Google Ads

- Request or confirm an active Google Ads developer token
- Create OAuth client credentials or a service account flow
- Generate a refresh token if using OAuth user flow
- Confirm the target `GOOGLE_ADS_CUSTOMER_ID`
- If using an MCC, set `GOOGLE_ADS_LOGIN_CUSTOMER_ID`

## Default assumptions

- Primary merge key is `date + campaign ID`, with campaign name fallback if IDs are missing
- GA4 uses session-level Google Ads campaign dimensions by default
- Main KPIs include clicks, cost, conversions, sessions, key events, revenue, ROAS, and CPA

## Notes

- `.env`, service account JSON files, and `google-ads.yaml` are ignored by `.gitignore`
- If live credentials are incomplete, the UI still works with deterministic demo data
