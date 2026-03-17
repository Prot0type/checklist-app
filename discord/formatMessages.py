import pytz

from classes.match import Match
from datetime import datetime
from typing import List

import requests
from commons import constants as cvar

def get_embed_color(matches: List[Match]) -> int:
    has_lost = any(match.get_bet_status() == 'LOST' for match in matches)
    all_won = all(match.get_bet_status() == 'WON' for match in matches)
    all_not_started = all(match.get_status() == 'NS' for match in matches)
    has_pending = any(match.get_bet_status() == 'PENDING' for match in matches)

    if has_lost:
        return 0xED4245  # RED
    elif all_won:
        return 0x57F287  # GREEN
    elif all_not_started:
        return 0x9B59B6  # PURPLE
    elif has_pending:
        return 0x00FFFF  # CYAN
    return 0x2C2F33  # Default Discord embed color


def get_embed_description(matches: List[Match]) -> str:
    # Sort matches first by start time, then by home team name if start times are the same
    sorted_matches = sorted(matches, key=lambda x: (x.get_start_time(), x.get_home_team()))
    description_lines = []

    # Define the EST timezone
    est = pytz.timezone("US/Eastern")

    for match in sorted_matches:
        # Determine the status symbol
        if match.get_bet_status() == 'WON':
            status_symbol = '✅'
        elif match.get_bet_status() == 'LOST':
            status_symbol = '❌'
        elif match.get_bet_status() == 'PENDING':
            if match.get_status() == 'NS':
                status_symbol = '🕒'
            elif match.get_status() == 'IP':
                status_symbol = '⚽'
            else:
                status_symbol = '❓'  # Just in case of unknown status
        else:
            status_symbol = '❓'

        # Format the start time in the desired format and convert to EST
        start_time_dt = datetime.fromisoformat(match.get_start_time().replace("Z", "+00:00")).astimezone(pytz.utc)
        start_time_est = start_time_dt.astimezone(est)
        start_time_str = start_time_est.strftime("%A, %I:%M %p EST")

        # Bold the team name that was wagered on
        if match.get_side_wagered_on() == 'HOME':
            home_team = f"**{match.get_home_team()}**"
            away_team = match.get_away_team()
        else:
            home_team = match.get_home_team()
            away_team = f"**{match.get_away_team()}**"

        # Use score if available, otherwise use 'vs'
        score = match.get_score()
        if score and score != 'N/A':
            match_line = f"{status_symbol} {home_team} {score} {away_team} - {start_time_str}"
        else:
            match_line = f"{status_symbol} {home_team} vs {away_team} - {start_time_str}"

        description_lines.append(match_line)

    return '\n'.join(description_lines)


def get_embed(checklist_name: str, matches: List[Match]) -> dict:
    embed = {
        "title": checklist_name,
        "description": get_embed_description(matches),
        "color": get_embed_color(matches)
    }
    return embed


#### TEST


def send_or_edit_discord_message(channel_id, checklist_name, matches, bot_token):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json"
    }

    # Generate the embed based on the current matches and checklist name
    embed = get_embed(checklist_name, matches)
    payload = {
        "embeds": [embed]
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("Message edited successfully")
    else:
        print(f"Failed to edit message: {response.status_code}, {response.text}")


# Example usage
if __name__ == "__main__":
    BOT_TOKEN = cvar.BOT_TOKEN
    CHANNEL_ID = cvar.CHANNEL_ID

    if not BOT_TOKEN or not CHANNEL_ID:
        raise ValueError("Set DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID before running this module directly.")

    # Example checklist and matches
    checklist_name = "Champions-League-11-Leg-Parlay"
    matches = [
        Match(
            match_url="https://example.com/match1",
            home_team="AC Milan",
            away_team="Club Brugge",
            side_wagered_on="HOME",
            start_time="2024-10-19T12:45:00+00:00",
            status="NS",
            bet_status="PENDING",
            score="3 - 1"
        ),
        Match(
            match_url="https://example.com/match2",
            home_team="Juventus",
            away_team="VfB Stuttgart",
            side_wagered_on="AWAY",
            start_time="2024-10-19T15:00:00+00:00",
            status="NS",
            bet_status="PENDING"
        ),
        Match(
            match_url="https://example.com/match3",
            home_team="Aston Villa",
            away_team="Bologna",
            side_wagered_on="AWAY",
            start_time="2024-10-19T15:00:00+00:00",
            status="NS",
            bet_status="PENDING"

        )
    ]

    # Send or edit the Discord message with the updated checklist
    send_or_edit_discord_message(CHANNEL_ID, checklist_name, matches, BOT_TOKEN)



#### TEST






# ✅
# ⚽
# ❌
# 🕒
# ❓
