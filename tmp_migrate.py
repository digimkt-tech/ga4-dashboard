from sites_manager import load_sites, add_site
from config import load_config

config = load_config()
sites = load_sites()

if not sites and config.ga4_property_id:
    add_site("主網站 (Legacy)", config.ga4_property_id, config.gsc_site_url or "")
    print("Migrated.")
else:
    print("Already migrated or no legacy config.")
