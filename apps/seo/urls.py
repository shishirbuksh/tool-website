from django.urls import path
from apps.seo import views

urlpatterns = [
    path("sitemap.xml", views.sitemap_xml, name="sitemap_xml"),
    path("sitemap-index.xml", views.sitemap_index_xml, name="sitemap_index_xml"),
    path("sitemap_index.xml", views.sitemap_index_xml, name="sitemap_index_underscore_xml"),
    path("sitemap-<str:locale>.xml", views.sitemap_locale_xml, name="sitemap_locale_xml"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("llms.txt", views.llms_txt, name="llms_txt"),
    path("<str:key>.txt", views.indexnow_key_file, name="indexnow_key_file"),
]
