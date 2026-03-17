import logging
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up Chrome options to specify the binary location
chrome_options = Options()
chrome_options.binary_location = '/usr/bin/chromium-browser'
chrome_options.add_argument('--headless')  # Run headless as no display
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

# Set up the path to ChromeDriver
service = Service('/usr/bin/chromedriver')

# Initialize the WebDriver with the specified Chrome options
default_driver = webdriver.Chrome(service=service, options=chrome_options)

def get_match_status(match_url, driver=default_driver):
    """
    Function to get match status and score from the given match URL.
    
    Parameters:
    driver (webdriver.Chrome, optional): Selenium WebDriver instance. Defaults to default_driver.
    match_url (str): The URL of the match.
    
    Returns:
    tuple: A tuple containing the match status (str) and score (str or bool).
           Status can be 'NS' (Not Started), 'IP' (In-Play), 'HT' (Half-Time), 'FT' (Full-Time).
           Score can be 'x - y' or False if not available.
    """
    try:
        # Navigate to the webpage
        driver.get(match_url)

        # Wait until the status wrapper is present (Increase timeout if necessary)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "css-1cf82ng-MFHeaderStatusWrapper"))
        )

        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find the status wrapper element
        status_wrapper_div = soup.find('div', class_='css-1cf82ng-MFHeaderStatusWrapper emg45p20')
        if not status_wrapper_div:
            return ('NS', False)

        # Determine match status
        status_text_element = status_wrapper_div.find('span', class_='css-xbwez1-MFStatusReason emg45p211')
        score_element = status_wrapper_div.find('span', class_='css-ktw5ic-MFHeaderStatusScore emg45p23')
        live_time_element = status_wrapper_div.find('div', class_='css-1dr9hlj-MFStatusLiveTime emg45p28')
        halftime_element = status_wrapper_div.find('span', class_='css-12193e3-MFStatusLiveTimeText emg45p29')

        print (halftime_element)

        # Default values
        status = 'NS'
        score = False

        # Determine status based on status text or live time element
        if halftime_element and halftime_element.text.lower() == 'half time':
            # If halftime_element is present and has text 'Half time', set status to 'HT'
            status = 'HT'
        elif live_time_element:
            # If the live time element is present, the match is In-Play
            status = 'IP'
        elif status_text_element:
            status_text = status_text_element.text.lower()
            if 'full time' in status_text:
                status = 'FT'
            else:
                status = 'NS'
        else:
            status = 'NS'

        # Extract the score if available
        if score_element:
            score = score_element.text.strip()

        return (status, score)
    except Exception as e:
        logger.error("Error occurred while trying to get match status: %s", e)
        return ('NS', False)

def get_match_datetime(match_url, driver=default_driver):
    """
    Function to get match date and time from the given match URL.
    
    Parameters:
    driver (webdriver.Chrome, optional): Selenium WebDriver instance. Defaults to default_driver.
    match_url (str): The URL of the match.
    
    Returns:
    str: The match date and time if found.
    bool: False if the datetime element is not found.
    """
    try:
        # Navigate to the webpage
        driver.get(match_url)

        # Wait until the datetime element is present (Increase timeout if necessary)
        datetime_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "time"))
        )

        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find the datetime element using the 'time' tag
        datetime_tag = soup.find('time', attrs={"datetime": True})
        if datetime_tag:
            return datetime_tag['datetime']  # Extract the datetime attribute
        else:
            return False
    except Exception as e:
        logger.error("Error occurred while trying to get match datetime: %s", e)
        return False


def get_match_teams(match_url, driver=default_driver):
    """
    Function to get the home and away team names from the given match URL.
    
    Parameters:
    driver (webdriver.Chrome, optional): Selenium WebDriver instance. Defaults to default_driver.
    match_url (str): The URL of the match.
    
    Returns:
    tuple: A tuple containing the home team name and away team name (str, str).
    """
    try:
        # Navigate to the webpage
        driver.get(match_url)

        # Wait until the team names are present (Increase timeout if necessary)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "css-dpbuul-TeamNameItself-TeamNameOnTabletUp"))
        )

        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find team names
        team_name_elements = soup.find_all('span', class_='css-dpbuul-TeamNameItself-TeamNameOnTabletUp e2bgjnh1')
        if len(team_name_elements) >= 2:
            home_team = team_name_elements[0].text.strip()
            away_team = team_name_elements[1].text.strip()
            return (home_team, away_team)
        else:
            logger.error("Could not find both team names on the page.")
            return (None, None)
    except Exception as e:
        logger.error("Error occurred while trying to get match teams: %s", e)
        return (None, None)


def main():
    # Example usage of the get_match_status function
    match_url = "https://www.fotmob.com/matches/athletic-club-vs-mallorca/2dsrjx#4506857"
    match_status, match_score = get_match_status(match_url)
    logger.info("Match Status: %s, Match Score: %s", match_status, match_score)

    # Get Match Date and Time
    match_datetime = get_match_datetime(match_url)
    if match_datetime:
        logger.info("Match Date and Time (ISO Format): %s", match_datetime)
    else:
        logger.info("Date and Time not found or not available yet.")

    # Get Home and Away Team Names
    home_team, away_team = get_match_teams(match_url)
    if home_team and away_team:
        logger.info("Home Team: %s, Away Team: %s", home_team, away_team)
    else:
        logger.info("Team names not found or not available yet.")

if __name__ == "__main__":
    try:
        main()
    finally:
        default_driver.quit()
