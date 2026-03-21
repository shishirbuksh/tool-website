import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_sitemap_xml():
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"
    content = response.text
    # Check if the correct domain is present and the typo is fixed
    assert "https://storybrainai.com/" in content
    assert "https://stroybrainai.com/" not in content

def test_robots_txt():
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    content = response.text
    assert "Sitemap: https://storybrainai.com/sitemap.xml" in content
    assert "https://stroybrainai.com/" not in content

def test_homepage_seo_tags():
    response = client.get("/")
    assert response.status_code == 200
    content = response.text
    # Verify the title tag
    assert "<title>Home | StoryBrain AI</title>" in content or "StoryBrain AI" in content
    # Verify Open Graph tags
    assert 'property="og:title" content="StoryBrain AI - Free Online Utilities"' in content
    assert 'property="og:url" content="https://storybrainai.com/"' in content
    assert 'name="description" content="StoryBrain AI' in content
    # Verify schema.org injection
    assert '"name": "StoryBrain AI"' in content
    assert '"url": "https://storybrainai.com/"' in content

def test_tools_pages_exist():
    tools = [
        "age-calculator",
        "percentage-calculator",
        "password-generator",
        "qr-generator",
        "base64-tool"
    ]
    for tool in tools:
        response = client.get(f"/tool/{tool}")
        assert response.status_code == 200
        assert "StoryBrain AI" in response.text
