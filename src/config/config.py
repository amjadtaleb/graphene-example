import tomllib
from pathlib import Path

import msgspec


class Database(msgspec.Struct):
    name: str
    user: str
    password: str
    host: str
    port: int


class SMTP2Go(msgspec.Struct):
    webhook_token: str  # our token the provider uses for authentication
    api_token: str
    domain_id: str  # not necessary to query users
    smtp_host: str
    smtp_port: int


class Mailersend(msgspec.Struct):
    webhook_token: str
    api_token: str
    domain_id: str
    smtp_host: str
    smtp_port: int

class Usage(msgspec.Struct):
    hobby_monthly_limit: int

class Config(msgspec.Struct):
    database: Database
    smtp2go: SMTP2Go
    mailersend: Mailersend
    usage: Usage


CONFIG_PATH = Path(__file__).parent.parent.parent / "config.toml"


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load the config file and return a Config object."""
    with path.open("rb") as f:
        data = tomllib.load(f)
    return msgspec.convert(data, type=Config)


# Load the config once when the module is imported
config = load_config()
