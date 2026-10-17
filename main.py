import os

import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = os.path.dirname(os.path.abspath(__file__))

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

ALIASES = {"num_workers": "workers"}


def norm_key(k: str) -> str:
    k = k.strip().lower()
    return ALIASES.get(k, k)


def load_yaml(env: str) -> dict:
    path = os.path.join(BASE, f"config.{env}.yaml")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return {norm_key(str(k)): v for k, v in data.items()}


def load_dotenv() -> dict:
    path = os.path.join(BASE, ".env")
    out = {}
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k.upper().startswith("APP_"):
                k = k[4:]
            out[norm_key(k)] = v
    return out


def load_os_env() -> dict:
    out = {}
    for k, v in os.environ.items():
        if k.startswith("APP_") and k.upper() != "APP_ENV":
            out[norm_key(k[4:])] = v
    return out


def coerce(key: str, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes", "on")
    return str(value)


@app.get("/effective-config")
def effective_config(set: list[str] | None = Query(default=None)):
    env = os.environ.get("APP_ENV", "development")
    merged = dict(DEFAULTS)
    merged.update(load_yaml(env))
    merged.update(load_dotenv())
    merged.update(load_os_env())

    for item in set or []:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        merged[norm_key(k)] = v.strip()

    result = {k: coerce(k, v) for k, v in merged.items()}
    result["api_key"] = "****"
    return result
