"""Shared paths, model access, and cost limits for the Campus Customs homework."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from genai_prices import Usage, calc_price
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
PRODUCTS_DIR = DATA_DIR / "products"
PROFILES_DIR = PROJECT_DIR / "profiles"
OUTPUT_DIR = PROJECT_DIR / "output"
CATALOGUE_JSON_PATH = OUTPUT_DIR / "catalogue.json"
CATALOGUE_DB_PATH = OUTPUT_DIR / "catalogue.db"

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
DEFAULT_MODEL = "gpt-6-astra"
# The one-off catalogue build describes 102 photos, so it uses the smaller model.
DEFAULT_CATALOGUE_MODEL = "gpt-5.6-luna"
# No single agent loop may spend more than this in tokens.
MAX_LOOP_USD = Decimal("0.50")


def load_environment() -> None:
    """Load the nearest .env, walking up from this folder to the course root."""

    for folder in [PROJECT_DIR, *PROJECT_DIR.parents]:
        if (folder / ".env").is_file():
            load_dotenv(folder / ".env")
            break


def model_name() -> str:
    """The one place the agents' model name is read."""

    load_environment()
    return os.getenv("OPENAI_MODEL") or DEFAULT_MODEL


def catalogue_model_name() -> str:
    """The model used only by build_catalogue.py."""

    load_environment()
    return os.getenv("CATALOGUE_MODEL") or DEFAULT_CATALOGUE_MODEL


def build_model(name: str | None = None) -> OpenAIResponsesModel:
    """gpt-6-astra only accepts structured output and tools on the Responses API."""

    load_environment()
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing. Add it to the MGT409 root .env.")
    return OpenAIResponsesModel(
        name or model_name(),
        provider=OpenAIProvider(api_key=api_key, base_url=PORTKEY_BASE_URL),
    )


def price_usd(input_tokens: int, output_tokens: int, name: str | None = None) -> Decimal | None:
    """Price a call from the published per-token rates; None if the model is unlisted.

    Portkey answers as a regional deployment name, so the provider does not report cost
    itself. Pricing by the configured model name keeps the budget enforceable.
    """

    try:
        price = calc_price(
            Usage(input_tokens=input_tokens, output_tokens=output_tokens),
            model_ref=name or model_name(),
            provider_id="openai",
        )
    except LookupError:
        return None
    return Decimal(str(price.total_price))


def inside_sandbox(path: Path, root: Path = PROJECT_DIR) -> Path:
    """Resolve a path and refuse anything outside the project folder."""

    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise PermissionError(f"Path is outside the sandbox: {resolved}")
    return resolved
