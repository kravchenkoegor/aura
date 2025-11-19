from typing import Any


def parse_cors(v: Any) -> list[str] | str:
  """Parse CORS origins from comma-separated string or list."""

  if isinstance(v, str) and not v.startswith("["):
    return [i.strip() for i in v.split(",")]

  elif isinstance(v, list | str):
    return v

  raise ValueError(v)
