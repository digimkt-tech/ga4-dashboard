import json
from pathlib import Path
from dataclasses import dataclass, asdict

SITES_FILE = Path(__file__).resolve().parent / "sites.json"

@dataclass
class SiteConfig:
    domain_name: str
    ga4_property_id: str
    gsc_site_url: str

def load_sites() -> list[SiteConfig]:
    if not SITES_FILE.exists():
        return []
    try:
        data = json.loads(SITES_FILE.read_text(encoding="utf-8"))
        return [SiteConfig(**s) for s in data]
    except Exception as e:
        print(f"Error loading sites.json: {e}")
        return []

def save_sites(sites: list[SiteConfig]):
    data = [asdict(s) for s in sites]
    SITES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def add_site(domain_name: str, ga4_property_id: str, gsc_site_url: str):
    sites = load_sites()
    # Check if domain exists, if so update it
    for s in sites:
        if s.domain_name == domain_name:
            s.ga4_property_id = ga4_property_id
            s.gsc_site_url = gsc_site_url
            save_sites(sites)
            return
            
    sites.append(SiteConfig(domain_name=domain_name, ga4_property_id=ga4_property_id, gsc_site_url=gsc_site_url))
    save_sites(sites)

def remove_site(domain_name: str):
    sites = load_sites()
    sites = [s for s in sites if s.domain_name != domain_name]
    save_sites(sites)
