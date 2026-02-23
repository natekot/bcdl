import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "bcdl"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")


def get_identity_cookie() -> str | None:
    return load_config().get("identity")


def set_identity_cookie(identity: str) -> None:
    config = load_config()
    config["identity"] = identity
    save_config(config)
