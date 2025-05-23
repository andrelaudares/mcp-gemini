from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Load settings from .env file, case-insensitive keys
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', case_sensitive=False)

    omie_app_key: str = Field(..., alias='OMIE_APP_KEY')
    omie_app_secret: str = Field(..., alias='OMIE_APP_SECRET')
    omie_api_base_url: str = "https://app.omie.com.br/api/v1"
    google_api_key: str = Field(..., alias='GOOGLE_API_KEY')

# Load settings - will raise error if .env is missing or vars aren't set
try:
    settings = Settings()
except ValidationError as e:
    print(f"Erro ao carregar configuracoes. Verifique se o arquivo .env existe e contem OMIE_APP_KEY, OMIE_APP_SECRET e GOOGLE_API_KEY.\n{e}")
    exit(1) 