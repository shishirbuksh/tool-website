"""Extract all tool data from existing services into a single data/tools.yaml"""
import os
import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import Settings
from app.services.catalog_service import CatalogService
from app.services.seo_service import SeoService
from app.services.sitemap_service import SitemapService

settings = Settings()
catalog = CatalogService(settings)
seo_svc = SeoService(settings)
sitemap_svc = SitemapService(settings)

tools_data = {}
cat_tools, _ = catalog.get_categorized_tools()
slug_to_category = {}
for cat_name, tools in cat_tools.items():
    for t in tools:
        slug = t["url"].replace("/tool/", "")
        slug_to_category[slug] = cat_name

for slug in sorted(catalog.get_valid_tools()):
    seo = seo_svc.get_seo(slug)
    pri = sitemap_svc._get_pri(slug)
    tools_data[slug] = {
        "name": seo.name,
        "icon": seo.icon,
        "category": slug_to_category.get(slug, "Productivity & Utilities"),
        "description": seo.description,
        "keywords": seo.keywords,
        "app_category": seo.app_category,
        "sitemap_priority": pri,
        "date_modified": seo.date_modified,
        "faqs": seo.faqs,
        "howto_steps": seo.howto_steps,
        "howto_calculate": seo.howto_calculate,
        "about_title": seo.about_title,
        "about_body": seo.about_body,
        "related_slugs": seo.related_slugs,
    }

out_dir = os.path.join(settings.base_dir, "data")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "tools.yaml")
with open(out_path, "w", encoding="utf-8") as f:
    yaml.dump({"tools": tools_data}, f, allow_unicode=True, sort_keys=False, width=120)

print(f"Wrote {len(tools_data)} tools to {out_path}")
