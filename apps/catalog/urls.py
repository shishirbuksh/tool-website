from django.urls import path, re_path
from apps.catalog import views

urlpatterns = [
    path("", views.home, name="home"),
    path("tools", views.tools_page, name="tools_page"),
    path("directory", views.directory_redirect, name="directory_redirect"),
    path("tool/<slug:tool_name>", views.tool_detail, name="tool_detail"),
    path("api/tools/catalog", views.tools_catalog_api, name="tools_catalog_api"),
    path("api/contact", views.contact_submission, name="contact_submission"),

    # Legacy locale redirects (/hi, /es, /fr, /de, /hi/*, etc.)
    re_path(r"^(?:hi|es|fr|de)(?:/(?P<rest_path>.*))?$", views.legacy_locale_redirect, name="legacy_locale_redirect"),

    # Dynamic page or hub routing
    path("<slug:page_name>", views.hub_or_page, name="hub_or_page"),
]
