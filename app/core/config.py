import os

class Settings:
    PROJECT_NAME: str = "Multi-Tool Website"
    # E:/ruff1/tool/app/core/config.py -> BASE_DIR becomes E:/ruff1/tool
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
    
    @property
    def TEMPLATES_DIR(self):
        return os.path.join(self.BASE_DIR, "templates")

    @property
    def STATIC_DIR(self):
        return os.path.join(self.BASE_DIR, "static")

settings = Settings()
