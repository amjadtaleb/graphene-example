import tomllib
from pathlib import Path

import msgspec


class Database(msgspec.Struct):
    name: str
    user: str
    password: str
    host: str
    port: int


class Config(msgspec.Struct):
    database: Database


CONFIG_PATH = Path(__file__).parent.parent.parent / "config.toml"


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load the config file and return a Config object."""
    with path.open("rb") as f:
        data = tomllib.load(f)
    return msgspec.convert(data, type=Config)


# Load the config once when the module is imported
config = load_config()
