"""Tests for Settings: directory resolution, defaults, and singleton behavior."""

import os

from app.core.config import Settings


class TestSettings:
    def test_base_dir_is_absolute(self):
        s = Settings()
        assert os.path.isabs(s.base_dir)

    def test_templates_dir_ends_with_templates(self):
        s = Settings()
        assert s.templates_dir.endswith("templates")
        assert os.path.isabs(s.templates_dir)

    def test_static_dir_ends_with_static(self):
        s = Settings()
        assert s.static_dir.endswith("static")
        assert os.path.isabs(s.static_dir)

    def test_default_project_name(self):
        s = Settings()
        assert s.PROJECT_NAME == "Multi-Tool Website"

    def test_settings_singleton(self):
        from app.core.config import settings

        assert settings.PROJECT_NAME == "Multi-Tool Website"

    def test_asset_version_tracks_bundle_hash_even_in_prod(self, tmp_path, monkeypatch):
        from app.core.config import _DynamicAssetVersion

        css_dir = tmp_path / "css"
        css_dir.mkdir(parents=True)
        css_file = css_dir / "app.css"
        css_file.write_text(".a{color:red}", encoding="utf-8")

        monkeypatch.setenv("APP_VERSION", "394640c")
        av = _DynamicAssetVersion(str(tmp_path))
        v1 = str(av)
        assert v1.startswith("394640c-")

        css_file.write_text(".a{color:blue}.lg\\:col-span-6{grid-column:span 6}", encoding="utf-8")
        v2 = str(av)
        assert v2.startswith("394640c-")
        assert v2 != v1
