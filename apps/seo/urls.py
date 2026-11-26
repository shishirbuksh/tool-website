from django.urls import path
from apps.seo import views

urlpatterns = [
    path("sitemap.xml", views.sitemap_xml, name="sitemap_xml"),
    path("sitemap-index.xml", views.sitemap_index_xml, name="sitemap_index_xml"),
    path("sitemap_index.xml", views.sitemap_index_xml, name="sitemap_index_underscore_xml"),
    path("sitemap-<str:locale>.xml", views.sitemap_locale_xml, name="sitemap_locale_xml"),
    path("page-sitemap.xml", views.sitemap_index_xml, name="page_sitemap_xml"),
    path("post-sitemap.xml", views.sitemap_index_xml, name="post_sitemap_xml"),
    path("pages-sitemap.xml", views.sitemap_index_xml, name="pages_sitemap_xml"),
    path("posts-sitemap.xml", views.sitemap_index_xml, name="posts_sitemap_xml"),
    path("category-sitemap.xml", views.sitemap_index_xml, name="category_sitemap_xml"),
    path("tools-sitemap.xml", views.sitemap_index_xml, name="tools_sitemap_xml"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("robot.txt", views.robots_alias, name="robot_txt_alias"),
    path("llms.txt", views.llms_txt, name="llms_txt"),
    path("<str:key>.txt", views.indexnow_key_file, name="indexnow_key_file"),
]
