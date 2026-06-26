import os

from app.core.config import Settings


class TestSettings:
    def test_base_dir_is_absolute(self):
        s = Settings()
        assert os.path.isabs(s.BASE_DIR)

    def test_templates_dir_ends_with_templates(self):
        s = Settings()
        assert s.TEMPLATES_DIR.endswith("templates")
        assert os.path.isabs(s.TEMPLATES_DIR)

    def test_static_dir_ends_with_static(self):
        s = Settings()
        assert s.STATIC_DIR.endswith("static")
        assert os.path.isabs(s.STATIC_DIR)

    def test_default_project_name(self):
        s = Settings()
        assert s.PROJECT_NAME == "Multi-Tool Website"

    def test_settings_singleton(self):
        from app.core.config import settings
        assert settings.PROJECT_NAME == "Multi-Tool Website"
