from __future__ import annotations

from checklist_app.integrations.fotmob_client import FotMobClient


def get_match_status(match_url, driver=None):
    client = FotMobClient()
    try:
        state = client.fetch_match_state(match_url)
        return state.status.value, state.score
    finally:
        client.close()


def get_match_datetime(match_url, driver=None):
    client = FotMobClient()
    try:
        state = client.fetch_match_state(match_url)
        return state.start_time.isoformat()
    finally:
        client.close()


def get_match_teams(match_url, driver=None):
    client = FotMobClient()
    try:
        state = client.fetch_match_state(match_url)
        return state.home_team, state.away_team
    finally:
        client.close()
