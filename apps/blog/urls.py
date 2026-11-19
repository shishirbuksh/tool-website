from django.urls import path
from apps.blog import views

urlpatterns = [
    path("blog", views.blog_index, name="blog_index"),
    path("blog/<slug:pillar>", views.blog_pillar, name="blog_pillar"),
    path("blog/<slug:pillar>/<slug:cluster>", views.blog_post, name="blog_post"),
]
