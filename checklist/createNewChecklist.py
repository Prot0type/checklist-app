import boto3
import csv
import logging
import os

from botocore.exceptions import ClientError
from classes.match import Match
from datetime import datetime, timedelta
from discord import discordFunctions as fm
from fotmob import fotmobScraper as fs
from typing import Dict, List, Tuple


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Initialize DynamoDB resource
client = boto3.resource('dynamodb', region_name='us-west-2')
checklist_table = client.Table('Checklist')
match_data_table = client.Table('MatchData')

# Directory where the CSV files are stored
CSV_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', 'checklist_csvs')

def process_csv_and_update_dynamodb(csv_filename: str) -> None:
    """
    Process a CSV file and update the DynamoDB tables Checklist and MatchData.

    Parameters:
    csv_filename (str): The filename of the CSV to be processed.

    Returns:
    None
    """

    # Construct full path to the CSV file
    csv_filepath = os.path.abspath(os.path.join(CSV_DIRECTORY, csv_filename))

    # Read CSV and collect data
    wagers: List[Dict[str, str]] = []
    matches: List[Match] = []
    earliest_start_time: datetime = None
    latest_end_time: datetime = None

    try:
        with open(csv_filepath, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                wager = {
                    'match_url': row['match_url'],
                    'side_wagered_on': row['side_wagered_on']
                }
                wagers.append(wager)
        logger.info("Successfully read CSV file: %s", csv_filename)
    except FileNotFoundError as e:
        logger.error("CSV file not found: %s", e)
        return
    except Exception as e:
        logger.error("Error reading CSV file %s: %s", csv_filename, e)
        return

    # Extract checklist_name from filename (without the extension)
    checklist_name = csv_filename.split('.')[0]

    # Add or Update entries in MatchData table (Upsert)
    for wager in wagers:
        match_url = wager['match_url']
        side_wagered_on = wager['side_wagered_on']

        # Check if match_url already exists in MatchData table
        try:
            response = match_data_table.get_item(Key={'match_url': match_url})
            if 'Item' in response:
                logger.info("Match URL already exists in MatchData table: %s", match_url)
                match_data = response['Item']
                # Create Match object with data fetched from the database
                match = Match(
                    match_url=match_url,
                    home_team=match_data.get('home_team', 'Unknown'),
                    away_team=match_data.get('away_team', 'Unknown'),
                    side_wagered_on=side_wagered_on,
                    start_time=match_data.get('start_time'),
                    status=match_data.get('status', 'NS'),
                    bet_status=match_data.get('bet_status', 'PENDING'),
                    score=match_data.get('score', 'N/A')
                )
                matches.append(match)
                continue
        except ClientError as e:
            logger.error("Error checking MatchData table for match_url %s: %s", match_url, e.response['Error']['Message'])
            continue

        # Call get_match_status, get_match_datetime, and get_team_names functions
        prefix = "https://www.fotmob.com/matches/"
        match_status, match_score = fs.get_match_status(prefix + match_url)
        match_datetime = fs.get_match_datetime(prefix + match_url)
        home_team, away_team = fs.get_match_teams(prefix + match_url)

        if not match_datetime:
            logger.error("Match datetime not found for match_url: %s", match_url)
            continue

        # Calculate end_time as start_time + 2 hours
        start_time = datetime.fromisoformat(match_datetime.replace("Z", "+00:00"))
        end_time = start_time + timedelta(hours=2)

        # Format both datetime strings in ISO 8601 without milliseconds
        start_time_str = start_time.isoformat(timespec='seconds')
        end_time_str = end_time.isoformat(timespec='seconds')

        # Create Match object
        match = Match(
            match_url=match_url,
            home_team=home_team,
            away_team=away_team,
            side_wagered_on=side_wagered_on,
            start_time=start_time_str,
            status=match_status,
            bet_status='PENDING',
            score=match_score if match_score else 'N/A'
        )
        matches.append(match)

        # Update MatchData table with new entry
        try:
            match_data_table.update_item(
                Key={'match_url': match_url},
                UpdateExpression='SET side_wagered_on = :s, #st = :st_value, bet_status = :bet_status, score = :sc, start_time = :st_time, end_time = :e_time, home_team = :home_team, away_team = :away_team',
                ExpressionAttributeNames={
                    '#st': 'status'
                },
                ExpressionAttributeValues={
                    ':s': side_wagered_on,
                    ':st_value': match_status,
                    ':bet_status': 'PENDING',
                    ':sc': match_score if match_score else 'N/A',
                    ':st_time': start_time_str,
                    ':e_time': end_time_str,
                    ':home_team': home_team,
                    ':away_team': away_team
                },
                ReturnValues='UPDATED_NEW'
            )
            logger.info("Successfully updated MatchData table for match_url: %s", match_url)
        except ClientError as e:
            logger.error("Error updating MatchData table for match_url %s: %s", match_url, e.response['Error']['Message'])
            continue

        # Track earliest start_time and latest end_time
        if earliest_start_time is None or start_time < earliest_start_time:
            earliest_start_time = start_time
        if latest_end_time is None or end_time > latest_end_time:
            latest_end_time = end_time

    # Convert to ISO 8601 strings without milliseconds for consistency
    earliest_start_time_str = earliest_start_time.isoformat(timespec='seconds') if earliest_start_time else 'N/A'
    latest_end_time_str = latest_end_time.isoformat(timespec='seconds') if latest_end_time else 'N/A'

    # Create Discord message
    message_id = fm.create_discord_message(checklist_name, matches)

    # Add or Update entry in Checklist table with new fields for 'in_progress' and 'is_ended'
    try:
        checklist_table.update_item(
            Key={'checklist_name': checklist_name},
            UpdateExpression='SET wagers = :w, start_time = :st_time, end_time = :e_time, in_progress = :in_prog, is_settled = :is_set, message_id = :msg_id',
            ExpressionAttributeValues={
                ':w': wagers,
                ':st_time': earliest_start_time_str,
                ':e_time': latest_end_time_str,
                ':in_prog': False,
                ':is_set': False,
                ':msg_id': message_id
            },
            ReturnValues='UPDATED_NEW'
        )
        logger.info("Successfully updated Checklist table for checklist_name: %s", checklist_name)
    except ClientError as e:
        logger.error("Error updating Checklist table: %s", e.response['Error']['Message'])

# Example usage:
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        logger.error("Usage: python createNewChecklist.py <csv_filename>")
    else:
        process_csv_and_update_dynamodb(sys.argv[1])
