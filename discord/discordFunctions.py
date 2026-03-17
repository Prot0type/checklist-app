import logging
import requests
import time

from typing import List, Optional
from classes.match import Match
from commons import constants as cvar
from discord import formatMessages as fm


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_discord_message(checklist_name: str, matches: List[Match], channel_id: str = cvar.CHANNEL_ID, bot_token: str = cvar.BOT_TOKEN) -> Optional[str]:
    """
    Creates a new message in a specified Discord channel with the details of the checklist.

    Parameters:
    checklist_name (str): The name of the checklist.
    matches (List[Match]): A list of Match objects to include in the message.
    channel_id (str): The ID of the Discord channel to send the message to. Defaults to the channel ID in constants.
    bot_token (str): The bot token used to authenticate the request. Defaults to the bot token in constants.

    Returns:
    Optional[str]: The message ID if the message was sent successfully, None otherwise.
    """
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json"
    }

    # Generate the embed based on the current matches and checklist name
    embed = fm.get_embed(checklist_name, matches)
    payload = {
        "embeds": [embed]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        message_data = response.json()
        message_id = message_data['id']
        logger.info(f"Message sent successfully. Message ID: {message_id}")
        return message_id
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message: {e}")
        return None


def edit_discord_message(checklist_name: str, matches: List[Match], message_id: str, channel_id: str = cvar.CHANNEL_ID, bot_token: str = cvar.BOT_TOKEN) -> Optional[str]:
    """
    Edits an existing message in a specified Discord channel with updated details of the checklist.

    Parameters:
    checklist_name (str): The name of the checklist.
    matches (List[Match]): A list of Match objects to include in the updated message.
    message_id (str): The ID of the message to be edited.
    channel_id (str): The ID of the Discord channel where the message is located. Defaults to the channel ID in constants.
    bot_token (str): The bot token used to authenticate the request. Defaults to the bot token in constants.

    Returns:
    Optional[str]: The message ID if the message was edited successfully, None otherwise.
    """
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json"
    }

    # Generate the embed based on the current matches and checklist name
    embed = fm.get_embed(checklist_name, matches)
    payload = {
        "embeds": [embed]
    }

    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        message_data = response.json()
        logger.info(f"Message edited successfully. Message ID: {message_id}")
        return message_id
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to edit message: {e}")
        return None
