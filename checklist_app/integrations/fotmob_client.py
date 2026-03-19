from __future__ import annotations

import logging
import re
import shutil
import tempfile
from pathlib import Path
from dataclasses import dataclass, field

from checklist_app.domain.enums import MatchStatus
from checklist_app.domain.models import MatchState, parse_datetime


LOGGER = logging.getLogger(__name__)


class FotMobScraperError(RuntimeError):
    """Raised when FotMob data cannot be collected or parsed."""


@dataclass(slots=True)
class FotMobClient:
    wait_timeout_seconds: int = 20
    chrome_binary: str | None = None
    chromedriver_path: str | None = None
    _driver: object | None = field(default=None, init=False, repr=False)
    _profile_dir: Path | None = field(default=None, init=False, repr=False)

    BASE_URL: str = "https://www.fotmob.com/matches/"

    def close(self) -> None:
        if self._driver is None:
            if self._profile_dir is not None:
                self._cleanup_profile_dir()
            return

        try:
            self._driver.quit()
        finally:
            self._driver = None
            self._cleanup_profile_dir()

    def fetch_match_state(self, match_url: str) -> MatchState:
        soup = self._load_soup(match_url)
        start_time = self._extract_match_datetime(soup)
        if start_time is None:
            raise FotMobScraperError(f"Could not find a kickoff time for match '{match_url}'.")

        home_team, away_team = self._extract_team_names(soup)
        if not home_team or not away_team:
            raise FotMobScraperError(f"Could not find team names for match '{match_url}'.")

        status, score = self._extract_status_and_score(soup)
        return MatchState(
            match_url=match_url,
            home_team=home_team,
            away_team=away_team,
            start_time=parse_datetime(start_time),
            status=status,
            score=score,
        )

    def refresh_match_state(self, current_state: MatchState) -> MatchState:
        soup = self._load_soup(current_state.match_url)
        status, score = self._extract_status_and_score(soup)
        return MatchState(
            match_url=current_state.match_url,
            home_team=current_state.home_team,
            away_team=current_state.away_team,
            start_time=current_state.start_time,
            status=status,
            score=score,
        )

    def _load_soup(self, match_url: str):
        from bs4 import BeautifulSoup
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec
        from selenium.webdriver.support.ui import WebDriverWait

        if self._driver is None:
            options = Options()
            if self.chrome_binary:
                options.binary_location = self.chrome_binary
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            self._profile_dir = Path(tempfile.mkdtemp(prefix="checklist-app-chrome-"))
            options.add_argument(f"--user-data-dir={self._profile_dir}")

            if self.chromedriver_path:
                service = Service(self.chromedriver_path)
                self._driver = webdriver.Chrome(service=service, options=options)
            else:
                self._driver = webdriver.Chrome(options=options)

        full_url = match_url if match_url.startswith("http") else f"{self.BASE_URL}{match_url}"
        self._driver.get(full_url)

        try:
            WebDriverWait(self._driver, self.wait_timeout_seconds).until(
                ec.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception as exc:  # pragma: no cover - depends on live page timing
            LOGGER.warning("Timed out waiting for %s to load: %s", full_url, exc)

        return BeautifulSoup(self._driver.page_source, "html.parser")

    @staticmethod
    def _extract_status_and_score(soup) -> tuple[MatchStatus, str | None]:
        status_wrapper = FotMobClient._find_first_with_class_fragment(soup, "div", "MFHeaderStatusWrapper")
        if status_wrapper is None:
            return MatchStatus.NOT_STARTED, None

        status_text = FotMobClient._find_first_with_class_fragment(status_wrapper, "span", "MFStatusReason")
        score_text = FotMobClient._find_first_with_class_fragment(status_wrapper, "span", "MFHeaderStatusScore")
        live_time = FotMobClient._find_first_with_class_fragment(status_wrapper, "div", "MFStatusLiveTime")
        halftime_text = FotMobClient._find_first_with_class_fragment(status_wrapper, "span", "MFStatusLiveTimeText")

        if halftime_text and halftime_text.text.strip().lower() == "half time":
            status = MatchStatus.HALF_TIME
        elif live_time:
            status = MatchStatus.IN_PLAY
        elif status_text and "full time" in status_text.text.strip().lower():
            status = MatchStatus.FULL_TIME
        else:
            status = MatchStatus.NOT_STARTED

        score = score_text.text.strip() if score_text else None
        return status, score

    @staticmethod
    def _extract_match_datetime(soup) -> str | None:
        datetime_tag = soup.find("time", attrs={"datetime": True})
        if datetime_tag is None:
            return None
        return str(datetime_tag["datetime"])

    @staticmethod
    def _extract_team_names(soup) -> tuple[str | None, str | None]:
        names = FotMobClient._collect_unique_team_names(
            soup,
            [
                "TeamNameItself-TeamNameOnTabletUp",
                "TeamNameItself-TeamNameOnMobile",
                "-TeamName",
            ],
        )
        if len(names) >= 2:
            return names[0], names[1]

        title = soup.title.text.strip() if soup.title and soup.title.text else ""
        title_match = re.match(r"^(?P<home>.+?)\s+vs\s+(?P<away>.+?)\s+-", title)
        if title_match:
            return title_match.group("home").strip(), title_match.group("away").strip()

        return None, None

    @staticmethod
    def _find_first_with_class_fragment(node, tag_name: str, class_fragment: str):
        return node.find(
            tag_name,
            class_=lambda classes: bool(classes)
            and any(class_fragment in class_name for class_name in FotMobClient._normalize_classes(classes)),
        )

    @staticmethod
    def _collect_unique_team_names(soup, class_fragments: list[str]) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        for fragment in class_fragments:
            matches = soup.find_all(
                "span",
                class_=lambda classes: bool(classes)
                and any(fragment in class_name for class_name in FotMobClient._normalize_classes(classes)),
            )
            for match in matches:
                candidate = match.get_text(" ", strip=True)
                if not candidate or candidate in seen:
                    continue
                seen.add(candidate)
                names.append(candidate)
                if len(names) >= 2:
                    return names

        return names

    @staticmethod
    def _normalize_classes(classes) -> list[str]:
        if isinstance(classes, str):
            return classes.split()
        return list(classes)

    def _cleanup_profile_dir(self) -> None:
        if self._profile_dir is None:
            return

        try:
            shutil.rmtree(self._profile_dir, ignore_errors=True)
        except OSError:
            LOGGER.debug("Could not fully remove temporary Chromium profile directory %s", self._profile_dir)
        finally:
            self._profile_dir = None
