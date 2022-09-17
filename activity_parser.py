from bs4 import BeautifulSoup
from bs4.element import Tag
from dataclasses import dataclass
from typing import List


@dataclass
class Person:
    name: str
    locality: str
    isCurrent: bool  # is currently facilitating/participating
    isBahai: bool  # only used for participants; otherwise set to None.


@dataclass
class Activity:
    locality: str
    neighbourhood: str
    start_date: str
    stage: str  # grade, JY text, or Ruhi book depending on which type of activity this is
    facilitators: List[Person]
    participants: List[Person]
    doing_service_projects: bool  # JY group only; otherwise, this is None


class ActivityParser:
    def _parse_person_table(self, table: Tag) -> List[Person]:
        """Parse facilitators (teachers/animators/tutors) or participants out of a table of people.

        Args:
            table (Tag): A <tbody> table body tag corresponding to a table of facilitators or participants.

        Return: A list of persons extracted from the table"""
        people = []
        for row in table.find_all("tr"):
            name = None
            isBahai = None
            for cell in row.find_all("td"):
                if (
                    "basicIsCurrentCol" in cell["class"]
                    or "participantsIsCurrentCol" in cell["class"]
                ):
                    current = (
                        cell.span.has_attr("class") and "checked" in cell.span["class"]
                    )
                elif (
                    "basicNameCol" in cell["class"]
                    or "participantsNameCol" in cell["class"]
                ):
                    name = cell.button.text
                elif "participantsIsRegisteredBahaiCol" in cell["class"]:
                    isBahai = cell.span.text == "Yes"
                elif (
                    "basicLocalityCol" in cell["class"]
                    or "participantsLocalityCol" in cell["class"]
                ):
                    locality = cell.button.text
            if name is not None and isBahai is None:
                people.append(Person(name, locality, current, None))
            elif name is not None and isBahai is not None:
                people.append(Person(name, locality, current, isBahai))
        return people

    def parse(self, page_source: str) -> Activity:
        """Extract data on an activity from the SRPO page source code.

        Args:
            page_source (str): The full page source, retrieved after opening an activity page.

        Return: The Activity object parsed out of the page source."""
        soup = BeautifulSoup(page_source, "html.parser")
        tables = soup.find_all("tbody")
        try:
            [table_f] = [
                t
                for t in tables
                if t.has_attr("data-bind") and t["data-bind"] == "foreach: facilitators"
            ]
            facilitators = self._parse_person_table(table_f)
        except ValueError:
            # The table is probably missing because the activity doesn't have any facilitators set.
            facilitators = []
        try:
            [table_p] = [
                t
                for t in tables
                if t.has_attr("data-bind") and t["data-bind"] == "foreach: participants"
            ]
            participants = self._parse_person_table(table_p)
        except ValueError:
            # The table is probably missing because the activity doesn't have any participants set.
            participants = []

        [name] = [t for t in soup.find_all("h1") if "app-screen-title" in t["class"]]
        (stage, locality) = name.text.split(", ")

        for loc in soup.find_all("native-ui-location-field"):
            if "text: subdivisionName" in loc["params"]:
                # When the location field params refer to a subdivision, that seems to mean focus neighbourhood.
                [nbhd_tag] = loc.find_all("p")
                neighbourhood = nbhd_tag.text

        for date_field in soup.find_all("native-ui-date-field"):
            if "text: displayStartDate" in date_field["params"]:
                start_date = date_field.p.text
                break

        service_projects = None
        for p in soup.find_all("p"):
            if (
                p.has_attr("data-bind")
                and p["data-bind"] == "text: hasServiceProjectsText"
            ):
                service_projects = p.text == "Yes"

        return Activity(
            locality,
            neighbourhood,
            start_date,
            stage,
            facilitators,
            participants,
            service_projects,
        )
