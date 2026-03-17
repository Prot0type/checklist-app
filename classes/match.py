from typing import Optional


class Match:
    """
    Represents a soccer match with attributes such as teams, match status, score, and wagering information.

    Attributes:
        match_url (str): The URL of the match details page.
        home_team (str): The name of the home team.
        away_team (str): The name of the away team.
        side_wagered_on (str): The side that has been wagered on.
        start_time (str): The start time of the match.
        status (str): The current status of the match (e.g., 'NS', 'IP', 'HT', 'FT').
        bet_status(str): The current status of the bet (eg., 'PENDING', 'WON', 'LOST').
        score (Optional[str]): The current score of the match if available.
    """

    def __init__(self, match_url: str, home_team: str, away_team: str, side_wagered_on: str, start_time: str, status: str, bet_status: str, score: Optional[str] = None):
        self._match_url: str = match_url
        self._home_team: str = home_team
        self._away_team: str = away_team
        self._side_wagered_on: str = side_wagered_on
        self._start_time: str = start_time
        self._status: str = status
        self._bet_status: str = bet_status
        self._score: Optional[str] = score

    def get_match_url(self) -> str:
        """Returns the match URL."""
        return self._match_url

    def get_home_team(self) -> str:
        """Returns the name of the home team."""
        return self._home_team

    def get_away_team(self) -> str:
        """Returns the name of the away team."""
        return self._away_team

    def get_side_wagered_on(self) -> str:
        """Returns the side that has been wagered on."""
        return self._side_wagered_on

    def get_start_time(self) -> str:
        """Returns the start time of the match."""
        return self._start_time

    def get_status(self) -> str:
        """Returns the current status of the match."""
        return self._status

    def get_bet_status(self) -> str:
        """Returns the current status of the bet."""
        return self._bet_status

    def get_score(self) -> Optional[str]:
        """Returns the current score of the match, if available."""
        return self._score

    # Setters
    def set_match_url(self, match_url: str) -> None:
        """Sets the match URL."""
        self._match_url = match_url

    def set_home_team(self, home_team: str) -> None:
        """Sets the name of the home team."""
        self._home_team = home_team

    def set_away_team(self, away_team: str) -> None:
        """Sets the name of the away team."""
        self._away_team = away_team

    def set_side_wagered_on(self, side_wagered_on: str) -> None:
        """Sets the side that has been wagered on."""
        self._side_wagered_on = side_wagered_on

    def set_start_time(self, start_time: str) -> None:
        """Sets the start time of the match."""
        self._start_time = start_time

    def set_status(self, status: str) -> None:
        """Sets the current status of the match."""
        self._status = status

    def set_bet_status(self, bet_status: str) -> None:
        """Sets the current status of the bet."""
        self._bet_status = bet_status

    def set_score(self, score: Optional[str]) -> None:
        """Sets the current score of the match."""
        self._score = score
