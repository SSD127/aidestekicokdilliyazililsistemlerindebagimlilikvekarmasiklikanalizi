"""
config.py — Uygulama Konfigürasyonu

Bu dosya PolyMetric backend'inin tüm ayarlarını merkezi olarak yönetir.
.env dosyasından ortam değişkenlerini okuyarak Settings nesnesine dönüştürür.
Supabase bağlantı bilgileri, API anahtarları ve uygulama modu bu dosya üzerinden yönetilir.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Uygulamanın adı, çalışma ortamı ve hata ayıklama modu
    app_name: str = "PolyMetric Backend"
    app_env: str = "development"
    app_debug: bool = True

    # Supabase bağlantı bilgileri — .env dosyasından okunur
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None

    # Internal endpoint koruması için API anahtarı
    # Analiz motoru bu anahtarla /api/internal/* uçlarına erişir
    internal_api_key: str | None = None

    # AI yorum servisi için API anahtarları — ikisi de opsiyonel
    # OpenAI varsa öncelikli kullanılır, yoksa Gemini, o da yoksa rule-based fallback devreye girer
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    # .env dosyasını otomatik okur, büyük/küçük harf duyarsız
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    # Ayarları bir kez yükler ve önbelleğe alır; her istekte .env okumaz
    return Settings()
