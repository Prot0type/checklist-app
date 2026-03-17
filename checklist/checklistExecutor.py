import boto3
import logging
import os
import random
import time

from botocore.exceptions import ClientError
from classes.match import Match
from datetime import datetime, timedelta
from discord import discordFunctions as df
from fotmob import fotmobScraper as fs


def setup_logger(checklist_name):
    # Clear existing global handlers
    logging.getLogger().handlers.clear()

    # Create logs directory if it doesn't exist
    logs_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
    os.makedirs(logs_directory, exist_ok=True)

    # Generate unique log file name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"{checklist_name}_{timestamp}.log"
    log_filepath = os.path.join(logs_directory, log_filename)

    # Create a logger with a unique name
    logger = logging.getLogger(f"{checklist_name}_{timestamp}")

    # Avoid adding duplicate handlers if the logger is already set up
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)

        # Create file handler to write to the log file
        try:
            file_handler = logging.FileHandler(log_filepath)
            file_handler.setLevel(logging.INFO)
        except Exception as e:
            logger.info(f"Error creating FileHandler: {e}")  # Capture any file-related error

        # Create console handler to output to console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Define the logging format
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
checklist_table = dynamodb.Table('Checklist')
match_data_table = dynamodb.Table('MatchData')

def execute_checklist(checklist_name):

    # Initialize logger with unique filename for each checklist run
    logger = setup_logger(checklist_name)
    logger.info("Logger initialized successfully.")

    try:
        # Query the checklist table to get all wagers
        response = checklist_table.get_item(Key={'checklist_name': checklist_name})
        checklist = response.get('Item', {})

        if 'wagers' not in checklist:
            logger.warning(f"No wagers found for checklist '{checklist_name}'.")
            return

        wagers = checklist['wagers']
        matches = []  # Store Match objects locally

        # Initialize Match objects for each wager
        for wager in wagers:
            match_url = wager['match_url']
            side_wagered_on = wager['side_wagered_on']

            # Check if the match_url already exists in the MatchData table
            response = match_data_table.get_item(Key={'match_url': match_url})
            match_data = response.get('Item')

            if match_data:
                # Create a Match object with data from DynamoDB
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
            else:
                # If match doesn't exist in MatchData, scrape and create a new Match object
                logger.info(f"Adding new entry for match_url '{match_url}'.")
                prefix = "https://www.fotmob.com/matches/"
                full_url = prefix + match_url
                match_status, match_score = fs.get_match_status(full_url)
                match_datetime = fs.get_match_datetime(full_url)
                home_team, away_team = fs.get_match_teams(full_url)

                if match_datetime:
                    start_time = datetime.fromisoformat(match_datetime)
                    match = Match(
                        match_url=match_url,
                        home_team=home_team,
                        away_team=away_team,
                        side_wagered_on=side_wagered_on,
                        start_time=start_time.isoformat(),
                        status=match_status,
                        bet_status='PENDING',
                        score=match_score if match_score else 'N/A'
                    )
                else:
                    logger.error(f"Match datetime not found for match_url: {match_url}")
                    continue

            matches.append(match)

        # Loop every 30 seconds until all matches are settled
        while True:
            all_settled = True  # To check if all bets are settled

            # Iterate over each Match object and update if necessary
            for match in matches:
                # Call fotmobScraper to get the updated match status
                prefix = "https://www.fotmob.com/matches/"
                full_url = prefix + match.get_match_url()
                new_status, new_score = fs.get_match_status(full_url)

                # Normalize new_score to avoid incorrect comparisons
                if not new_score or new_score == False:
                    new_score = 'N/A'

                logger.info(f"{match.get_home_team()} vs {match.get_away_team()} - Live Status: {new_status}. Live Score {new_score}")

                # If the status or score has changed, update the Match object
                if new_status != match.get_status() or new_score != match.get_score():
                    logger.info(f"Updating match '{match.get_match_url()}': Status: {match.get_status()} -> {new_status}, Score: {match.get_score()} -> {new_score}")
                    match.set_status(new_status)
                    match.set_score(new_score if new_score else 'N/A')

                # Extract scores as integers
                if new_score and new_score != 'N/A':
                    home_score, away_score = map(int, new_score.split('-'))
                else:
                    home_score, away_score = 0, 0

                # Evaluate bet status based on score
                if match.get_side_wagered_on() == 'HOME':
                    if home_score >= away_score + 2:
                        match.set_bet_status('WON')
                    elif new_status == 'FT':
                        match.set_bet_status('WON' if home_score > away_score else 'LOST')
                elif match.get_side_wagered_on() == 'AWAY':
                    if away_score >= home_score + 2:
                        match.set_bet_status('WON')
                    elif new_status == 'FT':
                        match.set_bet_status('WON' if away_score > home_score else 'LOST')

                # If the bet status is still pending, mark all_settled as False
                if match.get_bet_status() == 'PENDING':
                    all_settled = False

                # Update DynamoDB MatchData table with new information
                match_data_table.update_item(
                    Key={'match_url': match.get_match_url()},
                    UpdateExpression='SET #st = :s, score = :sc, bet_status = :bs',
                    ExpressionAttributeNames={'#st': 'status'},
                    ExpressionAttributeValues={
                        ':s': match.get_status(),
                        ':sc': match.get_score() if match.get_score() else 'N/A',
                        ':bs': match.get_bet_status()
                    }
                )

                # Introduce a random sleep interval between 3 and 8 seconds
                random_sleep = random.randint(3, 8)
                logger.info(f"Sleeping for {random_sleep} seconds before checking next match.")
                time.sleep(random_sleep)

            # Call edit_discord_message to reflect changes in the Discord message
            message_id = checklist.get('message_id')
            if message_id:
                df.edit_discord_message(checklist_name, matches, message_id)

            # If all bets are settled, we end the checklist process
            if all_settled:
                logger.info(f"All bets in checklist '{checklist_name}' are settled. Ending checklist executor process.")

                # Update checklist entry to indicate completion
                checklist_table.update_item(
                    Key={'checklist_name': checklist_name},
                    UpdateExpression='SET in_progress = :val, is_settled = :settled',
                    ExpressionAttributeValues={':val': False, ':settled': True}
                )
                break  # Break out of the loop as all bets are settled

            # Wait for a random time interval between 40 to 50 seconds before the next full checklist check
            random_interval = random.randint(40, 50)
            logger.info(f"Sleeping for {random_interval} seconds before the next full checklist check.")
            time.sleep(random_interval)

    except ClientError as e:
        logger.error(f"Error executing checklist '{checklist_name}': {e.response['Error']['Message']}")
    except Exception as e:
        logger.error(f"Unexpected error executing checklist '{checklist_name}': {str(e)}")

# Example usage
if __name__ == "__main__":
    checklist_name = 'scythe-test-1'
    execute_checklist(checklist_name)
