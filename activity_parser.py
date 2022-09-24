import pdfme

from bs4 import BeautifulSoup
from bs4.element import Tag
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Person:
    """Represents a participant or facilitator"""

    name: str
    locality: str
    isCurrent: bool  # is currently facilitating/participating
    isBahai: bool  # only used for participants; otherwise set to None.

    def __str__(self):
        return (
            f"""{self.name} - {self.locality} - {"Baha'i" if self.isBahai else "FOF"}"""
        )


@dataclass
class Activity:
    """Represents a children's class, junior youth group, or study circle."""

    locality: str
    neighbourhood: str
    start_date: str
    stage: str  # grade, JY text, or Ruhi book depending on which type of activity this is
    facilitators: List[Person]
    participants: List[Person]
    doing_service_projects: bool  # JY group only; otherwise, this is None

    def __str__(self):
        return f"{self._get_activity_type()}, {self.stage} - {self.locality}"

    def _get_activity_type(self) -> str:
        """Get the activity type string for this activity, based on the content of the `stage` member.

        Note that for children's classes, the string will have a single-quote character instead of the special
        apostrophe that gets extracted from the SRPO source code.  This is necessary because the special quote
        breaks the PDF generator library.

        Return: One of "Study Circle", "Junior Youth Group", or "Children's Class" based on the content of the
            `stage` variable."""
        for ruhi_book in ActivityParser.study_circle_books:
            if self.stage.startswith(ruhi_book):
                return "Study Circle"
        for jy_text in ActivityParser.junior_youth_texts:
            if self.stage.startswith(jy_text):
                return "Junior Youth Group"
        for grade in ActivityParser.childrens_class_grades:
            if self.stage.startswith(grade):
                return "Children's Class"
        return "Unknown Activity Type"

    def _generate_participants_table(self) -> dict:
        """Generate the dictionary that specifies the table of participants.  This is one of the sections of the
        main PDF specification that is passed into the PDF generator."""
        # Study circles don't have a "currently participating" checkbox in the participants table
        has_current_col = self._get_activity_type() != "Study Circle"
        tablespec = {
            "widths": [2, 2, 1, 1] if has_current_col else [2.2, 2.2, 1.1],
            "style": "formtext",
            "table": [
                [
                    {
                        "colspan": 4 if has_current_col else 3,
                        "style": "formlabel",
                        ".": "Participants:",
                    },
                    None,
                    None,
                ]
                + ([None] if has_current_col else []),
                [
                    {".b": "Name"},
                    {".b": "Locality"},
                ]
                + ([{".b": "Currently Participating"}] if has_current_col else [])
                + [{".b": "Registered Bahá'í"}],
            ],
        }
        for participant in self.participants:
            rowspec = (
                [participant.name, participant.locality]
                + ([participant.isCurrent] if has_current_col else [])
                + [participant.isBahai]
            )
            tablespec["table"].append(rowspec)
        return tablespec

    def _generate_info_table(self):
        """Generate the top part of the PDF containing such things as the stage, locality, and list of facilitators.
        This is a list of rows of the table specified in the main PDF specification."""
        if self._get_activity_type() == "Children's Class":
            stage_type = "Grade"
            facilitator_type = "Teacher"
        elif self._get_activity_type() == "Junior Youth Group":
            stage_type = "Text"
            facilitator_type = "Animator"
        elif self._get_activity_type() == "Study Circle":
            stage_type = "Book"
            facilitator_type = "Tutor"
        else:
            stage_type = "Unknown stage"
            facilitator_type = "Unknown facilitator type"
        tablespec = [
            [
                f"{stage_type}:",
                {
                    "colspan": 2,
                    "style": "formtext",
                    ".": self.stage,
                },
                None,
                "Start Date:",
                {"style": "formtext", ".": self.start_date},
            ],
            [
                "Locality:",
                {"colspan": 2, "style": "formtext", ".": self.locality},
                None,
                "Neighbourhood:",
                {"style": "formtext", ".": self.neighbourhood},
            ],
        ]
        if self._get_activity_type() == "Junior Youth Group":
            tablespec.append(
                [
                    {
                        "colspan": 2,
                        "style": "formlabel",
                        ".": "Holding Service Projects:",
                    },
                    None,
                    {
                        "style": "formtext",
                        ".": "Yes" if self.doing_service_projects else "No",
                    },
                    None,
                    None,
                ],
            )
        tablespec += [
            [
                {"colspan": 5, "style": "formlabel", ".": " "},
                None,
                None,
                None,
                None,
            ],
            [
                f"{facilitator_type}{'s' if len(self.facilitators) > 1 else ''}:",
                {
                    "colspan": 4,
                    "style": "formtext",
                    ".": ", ".join([f.name for f in self.facilitators]),
                },
                None,
                None,
                None,
            ],
        ]
        return tablespec

    def generate_pdf(self, save_path: Path):
        """Generate a PDF for this activity and write it to a file.

        Args:
            save_path (Path): The PDF will be saved to a file at this path."""
        document = {
            "style": {
                "margin_bottom": 15,
                "text_align": "l",
                "page_size": "letter",
                "margin": [60, 50],
                "border_width": 0,
                "f": "Times",
            },
            "formats": {
                "title": {"b": 1, "s": 24},
                "formlabel": {"s": 15},
                "formtext": {"s": 12, "f": "Helvetica", "cell_margin_top": 8},
            },
            "sections": [
                {
                    "content": [
                        {
                            ".": f"{self._get_activity_type()} Info Sheet",
                            "style": "title",
                        },
                        {
                            "widths": [0.9, 1, 0.5, 1.2, 1.5],
                            "style": "formlabel",
                            "table": self._generate_info_table(),
                        },
                        self._generate_participants_table(),
                    ],
                },
            ],
        }
        with open(save_path, "wb") as f:
            pdfme.build_pdf(document, f)


class ActivityParser:
    childrens_class_grades = [f"Grade {x}" for x in range(1, 7)]
    study_circle_books = [f"Book {x}" for x in range(1, 8)] + [
        f"Book {x} (U{y})" for x in range(8, 15) for y in range(1, 4)
    ]
    junior_youth_texts = [
        "Breezes of Confirmation",
        "Wellspring of Joy",
        "Habits of an Orderly Mind",
        "Glimmerings of Hope",
        "Walking the Straight Path",
        "Learning About Excellence",
        "Thinking About Numbers",
        "Observation and Insight",
        "The Human Temple",
        "Drawing on the Power of the Word",
        "Spirit of Faith",
        "Power of the Holy Spirit",
    ]
    # this is the list of strings that identify the link to specific activities within the Activities page.
    all_activity_prefixes = (
        childrens_class_grades + study_circle_books + junior_youth_texts
    )

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
