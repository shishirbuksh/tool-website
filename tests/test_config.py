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
