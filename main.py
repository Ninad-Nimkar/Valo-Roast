import os
from pathlib import Path
from urllib.parse import quote
from openai import APIError, OpenAI
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from requests import RequestException

load_dotenv()


class Player(BaseModel):
    username: str
    tag: str


app = FastAPI()

# API keys
openai_api_key = os.getenv("OPENAI_API_KEY")
henrik_api_key = os.getenv("HENRIK_API_KEY")

HENRIK_BASE_URL = "https://api.henrikdev.xyz/valorant/v2/mmr/ap"
client = OpenAI(api_key=openai_api_key) if openai_api_key else None
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not INDEX_FILE.exists():
        return JSONResponse(
            status_code=500,
            content={"error": f"Missing homepage file: {INDEX_FILE}"},
        )
    return FileResponse(INDEX_FILE)


def api_error(message: str, status_code: int = 500, **extra):
    payload = {"error": message}
    payload.update(extra)
    return JSONResponse(status_code=status_code, content=payload)


def safe_json(response):
    try:
        return response.json()
    except ValueError:
        return None


def nested_value(data, *keys, default="N/A"):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current == default:
            return default
    return current if current not in (None, "") else default


def choose_season_stats(by_season, preferred_season):
    if not isinstance(by_season, dict) or not by_season:
        return {}

    preferred_stats = by_season.get(preferred_season)
    if isinstance(preferred_stats, dict):
        return preferred_stats

    season_stats = [stats for stats in by_season.values() if isinstance(stats, dict)]
    if not season_stats:
        return {}

    return max(season_stats, key=lambda stats: stats.get("number_of_games") or 0)


def upstream_error_message(payload, fallback):
    if isinstance(payload, dict):
        error = payload.get("error") or payload.get("errors") or payload.get("detail")
        if isinstance(error, dict):
            return error.get("message") or error.get("detail") or fallback
        if isinstance(error, list) and error:
            return str(error[0])
        if error:
            return str(error)
        if payload.get("message"):
            return str(payload["message"])
    return fallback


def extract_response_text(response):
    text = getattr(response, "output_text", "")
    return text.strip() if isinstance(text, str) else ""


@app.post("/player")
def get_player(player: Player):
    name = player.username.strip()
    tag = player.tag.strip().lstrip("#")

    if not name or not tag:
        return api_error("Enter both Riot ID and tagline.", status_code=400)

    encoded_name = quote(name, safe="")
    encoded_tag = quote(tag, safe="")
    url = f"{HENRIK_BASE_URL}/{encoded_name}/{encoded_tag}"
    headers = {"Authorization": henrik_api_key} if henrik_api_key else {}

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except RequestException:
        return api_error("Could not reach the HenrikDev API.", status_code=502)

    data = safe_json(response)

    if response.status_code != 200:
        message = upstream_error_message(data, "Failed to fetch player MMR data.")
        return api_error(message, status_code=502, upstream_status=response.status_code)

    if not isinstance(data, dict) or not isinstance(data.get("data"), dict):
        return api_error("HenrikDev returned an unexpected player data response.", status_code=502)

    player_data = data["data"]
    current_data = player_data.get("current_data", {})
    highest_rank = player_data.get("highest_rank", {})
    by_season = player_data.get("by_season", {})

    rank = nested_value(current_data, "currenttierpatched")
    highest_rank_name = nested_value(highest_rank, "patched_tier")
    season = nested_value(highest_rank, "season")
    rr = nested_value(current_data, "ranking_in_tier")
    elo = nested_value(current_data, "elo")
    last_change = nested_value(current_data, "mmr_change_to_last_game")
    season_stats = choose_season_stats(by_season, season)
    n_of_games = nested_value(season_stats, "number_of_games")
    wins = nested_value(season_stats, "wins")

    summary = f"""
    Rank: {rank}
    Highest Rank: {highest_rank_name}
    Highest rank season: {season}
    RR: {rr}
    ELO: {elo}
    Last Game RR Change: {last_change}
    No of games: {n_of_games}
    wins: {wins}

    """

    prompt = f"""
    You are a savage but funny esports analyst.

    Roast this Valorant player based on the stats.
    Be sarcastic but not hateful.

    Write a single sentence, not one sentence for every stat, and do not mention
    the raw stats directly.

    Add emojis if needed to make it funnier.

    Stats:
    {summary}
    """

    if client is None:
        return api_error("OPENAI_API_KEY is not configured.", status_code=503)

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )
    except APIError as exc:
        message = str(exc).strip() or "OpenAI failed to generate a roast."
        return api_error(message, status_code=502)

    roast_text = extract_response_text(response)
    if not roast_text:
        return api_error("OPENAI returned an unexpected completion response.", status_code=502)

    return {
        "stats": summary,
        "roast": roast_text,
    }
