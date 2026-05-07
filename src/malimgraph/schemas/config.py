import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: Optional[str] = Field(default=None, alias="NEO4J_PASSWORD")
    age_connection_uri: Optional[str] = Field(default=None, alias="AGE_CONNECTION_URI")
    llm_model: str = Field(default="claude-opus-4-7", alias="MALIMGRAPH_MODEL")
    max_concurrent_chunks: int = Field(default=5, alias="MALIMGRAPH_MAX_CONCURRENT")

    model_config = {"populate_by_name": True, "env_file": ".env"}


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
