from pydantic_settings import BaseSettings, SettingsConfigDict

PLAN_LIMITS: dict[str, dict[str, int]] = {
    "free": {"max_cameras": 3, "max_devices": 10},
    "pro": {"max_cameras": 20, "max_devices": 50},
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BulutSistem"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    public_api_url: str = "http://localhost:8000"

    database_url: str = "postgresql+asyncpg://bulut:bulut_secret@localhost:5433/bulutsistem"

    jwt_secret: str = "dev_secret_change_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    stream_token_expire_minutes: int = 15

    go2rtc_url: str = "http://localhost:1984"
    frigate_config_path: str = "/frigate_config/config.yml"
    frigate_api_url: str = "http://host.docker.internal:5000"

    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    public_mqtt_host: str = "localhost"
    public_mqtt_port: int = 1884
    mqtt_topic_prefix: str = "t"
    mqtt_service_user: str = "bulut_service"
    mqtt_service_password: str = "dev_service_mqtt_secret"
    mqtt_frigate_user: str = "bulut_frigate"
    mqtt_frigate_password: str = "dev_frigate_mqtt_secret"
    mqtt_passwd_path: str = "/mqtt_credentials/passwd"
    mqtt_acl_path: str = "/mqtt_credentials/acl"

    tunnel_internal_key: str = "dev_tunnel_internal_key"
    fcm_enabled: bool = False
    fcm_credentials_path: str = ""


settings = Settings()
