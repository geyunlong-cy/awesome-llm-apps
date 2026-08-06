from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    lark_app_id: str = Field(alias="LARK_APP_ID")
    lark_app_secret: str = Field(alias="LARK_APP_SECRET")
    lark_verification_token: str = Field(
        default="",
        alias="LARK_VERIFICATION_TOKEN",
    )
    lark_encrypt_key: str = Field(default="", alias="LARK_ENCRYPT_KEY")

    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.6-terra", alias="OPENAI_MODEL")

    bot_name: str = Field(default="Leo AI", alias="BOT_NAME")
    require_mention_in_group: bool = Field(
        default=True,
        alias="REQUIRE_MENTION_IN_GROUP",
    )
    max_output_tokens: int = Field(default=1200, alias="MAX_OUTPUT_TOKENS")
    allowed_open_ids: str = Field(default="", alias="ALLOWED_OPEN_IDS")

    @property
    def allowed_sender_ids(self) -> set[str]:
        return {
            item.strip()
            for item in self.allowed_open_ids.split(",")
            if item.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
