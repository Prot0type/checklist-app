from __future__ import annotations

import importlib.util
import unittest

from checklist_app.domain.enums import MatchStatus
from checklist_app.integrations.fotmob_client import FotMobClient


class FotMobClientParsingTests(unittest.TestCase):
    def _make_soup(self, html: str):
        if importlib.util.find_spec("bs4") is None:
            self.skipTest("bs4 is not installed in the current interpreter.")

        from bs4 import BeautifulSoup

        return BeautifulSoup(html, "html.parser")

    def test_extract_team_names_uses_stable_class_fragment_and_deduplicates(self) -> None:
        soup = self._make_soup(
            """
            <html>
              <head>
                <title>Mallorca vs Athletic Club - live score</title>
              </head>
              <body>
                <span class="css-dpbuul-TeamNameItself-TeamNameOnTabletUp ekrcg521">Mallorca</span>
                <span class="css-dpbuul-TeamNameItself-TeamNameOnTabletUp ekrcg521">Athletic Club</span>
                <span class="css-dpbuul-TeamNameItself-TeamNameOnTabletUp ekrcg521">Mallorca</span>
              </body>
            </html>
            """,
        )

        self.assertEqual(FotMobClient._extract_team_names(soup), ("Mallorca", "Athletic Club"))

    def test_extract_team_names_falls_back_to_title(self) -> None:
        soup = self._make_soup(
            """
            <html>
              <head>
                <title>Mallorca vs Athletic Club - live score</title>
              </head>
              <body></body>
            </html>
            """,
        )

        self.assertEqual(FotMobClient._extract_team_names(soup), ("Mallorca", "Athletic Club"))

    def test_extract_status_and_score_uses_stable_class_fragments(self) -> None:
        soup = self._make_soup(
            """
            <div class="css-1cf82ng-MFHeaderStatusWrapper abc123">
              <span class="css-xbwez1-MFStatusReason xyz456">Full Time</span>
              <span class="css-ktw5ic-MFHeaderStatusScore xyz456">2 - 1</span>
            </div>
            """,
        )

        self.assertEqual(FotMobClient._extract_status_and_score(soup), (MatchStatus.FULL_TIME, "2 - 1"))


if __name__ == "__main__":
    unittest.main()
