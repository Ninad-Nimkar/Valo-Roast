import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from pydantic import BaseModel
import requests
import json

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.staticfiles import StaticFiles
from fastapi import Request

class Player(BaseModel):
    username: str
    tag: str

app = FastAPI()

#API keys
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
henrik_api_key = os.getenv("HENRIK_API_KEY")

headers = {
    "Authorization": henrik_api_key
}

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/player")
def get_player(player: Player):
    name = player.username
    tag = player.tag

    url = f"https://api.henrikdev.xyz/valorant/v2/mmr/ap/{name}/{tag}"

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return{
            "error": "Failed to fetch data",
            "status_code": response.status_code
        }

    data = response.json()

    player_data = data["data"]

    rank = player_data["current_data"]["currenttierpatched"]
    Hrank = player_data["highest_rank"]["patched_tier"]
    season = player_data["highest_rank"]["season"]
    rr = player_data["current_data"]["ranking_in_tier"]
    elo = player_data["current_data"]["elo"]
    last_change = player_data["current_data"]["mmr_change_to_last_game"]
    n_of_games = player_data["by_season"]["e6a3"]["number_of_games"]
    wins = player_data["by_season"]["e6a3"]["wins"]

    summary = f"""
    Rank: {rank}
    Highest Rank: {Hrank}
    Highest rank season: {season}
    RR: {rr}
    ELO: {elo}
    Last Game RR Change: {last_change}
    No of games: {n_of_games}
    wins: {wins}

    """

    prompt = f"""
    You are a savage but funny esports analyst.

    Roast this Valorant player based on the stats
    Be sarcastic but not hateful.

    in a single sentence not different for every stat without mentioning the stats

    also add emojis if needed to make it funnier

    Stats:
    {summary}
    """ 
    
    response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": f"Bearer {openrouter_api_key}",

  },
  data=json.dumps({
    "model": "openai/gpt-5.2",
    "messages": [
      {
        "role": "system", "content": "You are a funny esports analyst.",
        "content": prompt
      }
    ],
    "max_tokens": 300,
    "temperature": 0.9
  })
)

    roast_json = response.json()
    roast_text = roast_json["choices"][0]["message"]["content"]

    return{
        "stats": summary,
        "roast": roast_text
    }
