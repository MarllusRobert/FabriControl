from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Valores de exemplo/desenvolvimento que nunca podem ir para produção.
_SEGREDOS_PADRAO = {"", "fabricontrol-dev-change-me", "troque-isto-em-producao"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FabriControl"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://fabri:fabri@localhost:5435/fabricontrol"
    jwt_secret: str = "fabricontrol-dev-change-me"
    jwt_expire_minutes: int = 600
    cors_origins: str = "http://localhost:3040,http://127.0.0.1:3040"
    login_max_tentativas: int = 5
    login_bloqueio_minutos: int = 15

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "producao", "prod")

    @property
    def cors_list(self) -> list[str]:
        return [origem.strip().rstrip("/") for origem in self.cors_origins.split(",") if origem.strip()]

    def problemas_producao(self) -> list[str]:
        problemas: list[str] = []
        if self.jwt_secret in _SEGREDOS_PADRAO or len(self.jwt_secret) < 32:
            problemas.append("JWT_SECRET precisa ser um valor próprio com 32+ caracteres.")
        if ":fabri@" in self.database_url:
            problemas.append("DATABASE_URL está com a senha padrão do banco.")
        if not self.cors_list or "*" in self.cors_list:
            problemas.append("CORS_ORIGINS precisa listar o(s) endereço(s) do front, sem '*'.")
        return problemas


@lru_cache
def get_settings() -> Settings:
    return Settings()
