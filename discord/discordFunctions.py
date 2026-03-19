from __future__ import annotations

from typing import List, Optional

from commons import constants as cvar
from discord import formatMessages as formatter


def create_discord_message(
    checklist_name: str,
    matches: List[object],
    channel_id: str = cvar.CHANNEL_ID,
    bot_token: str = cvar.BOT_TOKEN,
) -> Optional[str]:
    return formatter.send_or_edit_discord_message(channel_id, checklist_name, matches, bot_token)


def edit_discord_message(
    checklist_name: str,
    matches: List[object],
    message_id: str,
    channel_id: str = cvar.CHANNEL_ID,
    bot_token: str = cvar.BOT_TOKEN,
) -> Optional[str]:
    client = formatter.DiscordClient(bot_token=bot_token, channel_id=channel_id)
    return client.edit_checklist_message(checklist_name, formatter._adapt_matches(matches), message_id)
