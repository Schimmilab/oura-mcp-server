"""Configuration management for Oura MCP Server."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    requests_per_day: int = 5000


class OuraAPIConfig(BaseModel):
    """Oura API configuration."""
    base_url: str = "https://api.ouraring.com"
    # Optional since the OAuth2 migration (2026-08-29): with the authorization code
    # flow the access token is issued at runtime and refreshed automatically, so it
    # is no longer a required piece of static configuration.
    access_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    redirect_uri: str = "http://localhost:8080/callback"
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    timeout_seconds: int = 30


class CacheConfig(BaseModel):
    """Caching configuration."""
    enabled: bool = True
    ttl_seconds: int = 3600
    persistent: bool = False
    backend: str = "memory"  # memory | redis


class BaselinesConfig(BaseModel):
    """Baseline calculation configuration."""
    calculation_period_days: int = 30
    update_frequency: str = "daily"
    metrics: List[str] = Field(default_factory=lambda: [
        "hrv", "resting_hr", "temperature", "sleep_score", "readiness_score"
    ])


class SecurityConfig(BaseModel):
    """Security and privacy configuration."""
    access_level: str = "full"  # summary | standard | full
    audit_logging: bool = True
    audit_retention_days: int = 90


class OuraConfig(BaseModel):
    """Complete Oura configuration."""
    api: OuraAPIConfig
    cache: CacheConfig = Field(default_factory=CacheConfig)
    baselines: BaselinesConfig = Field(default_factory=BaselinesConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


class MCPServerConfig(BaseModel):
    """MCP server configuration."""
    name: str = "Oura Health MCP"
    version: str = "0.1.0"
    transport: str = "stdio"  # stdio | http
    http_port: int = 8080


class ResourcesConfig(BaseModel):
    """MCP resources configuration."""
    enabled: List[str] = Field(default_factory=lambda: [
        "sleep", "readiness", "activity", "hrv", "metrics"
    ])


class ToolsConfig(BaseModel):
    """MCP tools configuration."""
    enabled: List[str] = Field(default_factory=lambda: [
        "analyze_sleep_trend",
        "detect_recovery_status",
        "generate_daily_brief",
        "assess_training_readiness",
        "explain_metric_change",
    ])


class MCPConfig(BaseModel):
    """Complete MCP configuration."""
    server: MCPServerConfig = Field(default_factory=MCPServerConfig)
    resources: ResourcesConfig = Field(default_factory=ResourcesConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"  # json | text
    output: str = "stderr"  # stderr | stdout | file
    file_path: Optional[str] = "./logs/oura_mcp.log"


class Config(BaseModel):
    """Root configuration."""
    oura: OuraConfig
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file with environment variable substitution.

    Args:
        config_path: Path to config file. Defaults to config/config.yaml

    Returns:
        Parsed configuration object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
    """
    # Determine project root directory
    # From src/oura_mcp/utils/config.py -> project root
    project_root = Path(__file__).parent.parent.parent.parent

    # Load environment variables from .env in project root
    dotenv_path = project_root / ".env"
    load_dotenv(dotenv_path)

    # Determine config file path
    if config_path is None:
        config_path = os.getenv("OURA_MCP_CONFIG")
        if config_path is None:
            # Default: config/config.yaml relative to project root
            config_path = str(project_root / "config" / "config.yaml")

    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please copy config/config.example.yaml to config/config.yaml\n"
            f"Expected location: {config_file.absolute()}"
        )
    
    # Load YAML
    with open(config_file) as f:
        raw_config = yaml.safe_load(f)
    
    # Substitute environment variables
    raw_config = _substitute_env_vars(raw_config)
    
    # Parse and validate
    try:
        return Config(**raw_config)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")


_OPTIONAL_ENV_VARS = {
    "OURA_ACCESS_TOKEN",
    "OURA_REFRESH_TOKEN",
    "OURA_CLIENT_ID",
    "OURA_CLIENT_SECRET",
    "OURA_REDIRECT_URI",
}


def _substitute_env_vars(config: Any) -> Any:
    """
    Recursively substitute environment variables in config.
    
    Replaces ${VAR_NAME} with os.getenv('VAR_NAME').
    """
    if isinstance(config, dict):
        return {k: _substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_substitute_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Replace ${VAR_NAME} patterns
        if config.startswith("${") and config.endswith("}"):
            var_name = config[2:-1]
            value = os.getenv(var_name)
            if value is None:
                # Auth material is resolved at runtime by OuraAuth (OAuth2 flow) and
                # may legitimately be absent before the first authorization. Failing
                # here would make the server unstartable exactly when the user needs
                # it up in order to authorize.
                if var_name in _OPTIONAL_ENV_VARS:
                    return None
                raise ValueError(
                    f"Environment variable not set: {var_name}\n"
                    f"Please set it in .env or your environment"
                )
            return value
        return config
    else:
        return config


# Singleton instance
_config: Optional[Config] = None


def get_config(reload: bool = False) -> Config:
    """
    Get configuration singleton.
    
    Args:
        reload: Force reload from file
        
    Returns:
        Configuration instance
    """
    global _config
    
    if _config is None or reload:
        _config = load_config()
    
    return _config
