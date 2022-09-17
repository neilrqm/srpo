#!/usr/bin/env python3

import argparse
import logging
import pandas
import pyotp
import shutil
import time
import tempfile

from pathlib import Path
from typing import Any, Callable, List

from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    WebDriverException,
    SessionNotCreatedException,
    TimeoutException,
)

from activity_parser import Activity, ActivityParser


class find_element:
    """A callable suitable to use as a wait condition that extracts an element matching a given
    tag and accessible name."""

    def __init__(
        self,
        tag_name: str,
        name: str = None,
        text: str = None,
        comparator: Callable[[str, Any], bool] = None,
    ):
        """Get a new waiter object that determines the presence of an element that matches the given HTML tag,
        accessible name, and text value.

        The comparator parameter should define a function that takes two parameters and returns
        a boolean value.  This function will be used to compare the name or text (or both) of each tag examined
        to determine if the element matches the given criteria.  If the comparator is set to None, then
        the equality comparator will be used.  The element's name/text string will be passed into the comparator as the
        first parameter, and the `name` or `text` parameter passed into this object will be used as the second
        parameter.

        Args:
            tag_name (str): Search for an HTML element matching this tag.
            name (str): Accessible name to look for (or None to refrain from matching the accessible name)
            text (str): Text value to look for (or None to refrain from matching the text value)
            comparator (Callable): a function that takes 2 strings as paramters and resolves to a bool."""
        self.tag_name = tag_name
        self.name = name
        self.text = text
        self.comparator = comparator
        if self.comparator is None:
            # default comparactor is equality
            self.comparator = lambda s1, s2: s1 == s2

    def __call__(self, driver: webdriver):
        """Search for a matching element on the contents of a given web driver."""
        els = driver.find_elements(by=By.TAG_NAME, value=self.tag_name)
        for e in els:
            matches_name = self.name is None
            matches_text = self.text is None
            if self.name is not None:
                # get rid of non-ASCII characters and strip whitespace
                cleaned_name = (
                    e.accessible_name.encode("ascii", "ignore").decode().strip()
                )
                if self.comparator(cleaned_name, self.name):
                    matches_name = True
            if self.text is not None:
                if self.comparator(e.text, self.text):
                    matches_text = True
            if matches_name and matches_text:
                return e
        return False


class SRPO:
    def __init__(self, secret: str = None, output_dir: Path = None):
        """Create an object that can be used to access the SRPO.

        Args:
            secret (str): A base32-encoded secret string that can be used to generate TOTP tokens (see get_totp()).
            output_dir (Path): If this is not None, then data files that are downloaded will be copied into this
                folder before being deleted from the temporary directory."""
        self.logger = logging.getLogger("SRPO")
        self.driver = None
        self.secret = secret
        self.output_dir = output_dir
        self.parser = ActivityParser()

        self.download_dir = tempfile.TemporaryDirectory()
        exp = {"download.default_directory": self.download_dir.name}
        self.options = webdriver.ChromeOptions()
        self.options.headless = True
        self.options.add_experimental_option("prefs", exp)
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("--ignore-certificate-errors")
        self.options.add_argument("--allow-running-insecure-content")
        self.options.add_argument("--log-level=0")
        self.options.add_argument("--disable-extensions")
        self.options.add_argument("--proxy-server='direct://'")
        self.options.add_argument("--proxy-bypass-list=*")
        self.options.add_argument("--start-maximized")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--no-sandbox")

        self.childrens_class_grades = [f"Grade {x}" for x in range(1, 7)]
        self.study_circle_books = [f"Book {x}," for x in range(1, 8)] + [
            f"Book {x} (U{y})," for x in range(8, 15) for y in range(1, 4)
        ]
        self.junior_youth_texts = [
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
        self.all_activity_prefixes = (
            self.childrens_class_grades
            + self.study_circle_books
            + self.junior_youth_texts
        )

    def cleanup(self):
        """Exit the web browser and delete the temporary download directory."""
        self.download_dir.cleanup()
        self.driver.quit()

    def get_totp(self) -> str:
        """Get a time-based one-time password.

        This uses the secret passed into the SRPO object's constructor.  The secret is a base32-encoded string
        that is generated by the SRPO.  This secret can be acquired from the SRPO by reconfiguring the two-factor
        authentication source in the Tools menu.  Normally you would scan a QR code to configure your authenticator;
        instead, click the "QR Code not working" link.  This will display a string of characters that can be
        manually entered into the authenticator app.  This string is the secret string that is used to generate
        two-factor authentication codes (i.e. TOTP tokens).  You can save the string for use in this script,
        and also enter it into your authenticator app to have it generate TFA codes (or just scan the corresponding
        QR code into the app).

        Return: A 6-digit TOTP token in string format."""
        # this requires the secret string instead of taking a token on login because new tokens are required sometimes
        # during the session (e.g when downloading the regional list of individuals), in which case new tokens need to
        # be generated.  If this code ever gets stable and usable it might be preferable to allow the user to enter
        # TOTP tokens manually.
        totp = pyotp.TOTP(self.secret)
        return str(totp.now())

    def login(self, username: str, password: str):
        """Log into the SRPO.

        This function takes a two-factor authentication token for logging into the SRPO.  Note that tokens stay valid
        for a little while after they roll over in the authentication app.  It is not necessary to wait for the
        app to create a fresh token, even a token that is about to roll over will remain valid long enough for this
        function to complete the login procedure."""
        try:
            self.driver = webdriver.Chrome(
                chrome_options=self.options,
                desired_capabilities=DesiredCapabilities.CHROME,
            )
        except (SessionNotCreatedException, WebDriverException):
            self.driver = webdriver.Chrome(
                executable_path=ChromeDriverManager().install(),
                chrome_options=self.options,
                desired_capabilities=DesiredCapabilities.CHROME,
            )

        wait = WebDriverWait(self.driver, 10)
        self.driver.maximize_window()
        self.driver.get("https://cnd.onlinesrp.org/#/login")
        wait.until(find_element("input", name="Username")).send_keys(username)
        wait.until(find_element("input", name="Password")).send_keys(password)
        wait.until(find_element("button", name="Login")).click()
        wait.until(
            find_element(
                "input",
                name="Please enter a verification code from the Google Authenticator "
                "app on your mobile device to continue.",
            )
        ).send_keys(self.get_totp())
        wait.until(find_element("button", name="Continue")).click()

    def set_area(self, area: str, delay: float = 1.0):
        """Set the SRPO to filter data by a certain scope.

        It is expected that this is run on the home page that loads upon login, not other pages.

        Args:
            area (str): The name of the area as it appears in the SRPO's tree view.  For example, if the tree is:

                Canada
                    > British Columbia
                        > BC01 - Sooke
                        > BC02 - West Shore
                        > ...

                then setting the parameter to "British Columbia" will result in the BC region being selected as the
                SRPO's scope.  Setting the parameter to "BC01 - Sooke" will select that cluster as the scope, etc.

            delay (float): Wait for this long after the area is clicked.  It is necessary to wait for a bit to give
                the home page time to generate the SVG charts.  A few quick tests have indicated that 1 second is
                enough to give time for the charts to load.  However, it may not be necessary to wait for the graphics
                to load, in which case this parameter can be set to 0."""
        wait = WebDriverWait(self.driver, 10)
        wait.until(
            find_element("button", name="Canada", comparator=str.startswith)
        ).click()
        for _ in range(10):
            # wait until the tree that filters areas to be included in the dataset is displayed.  The tree elements
            # are defined as spans and there are a whole bunch of them, so we do this by waiting until there are
            # a whole bunch of spans in the page source.
            time.sleep(0.1)
            spans = self.driver.find_elements(by=By.TAG_NAME, value="span")
            if len(spans) > 100:
                break
        # Spans for the region name appear twice, we want to click on the furthest one down in the tree.
        max(
            [span for span in spans if span.text == area],
            key=lambda span: span.location["y"],
        ).click()
        time.sleep(delay)

    def _get_cycles_data(self, label: str) -> pandas.DataFrame:
        """Download a spreadsheet containing cycle data and load it into a pandas dataframe.

        The data will be downloaded as an Excel spreadsheet using the SRPO's export functionality.  The spreadsheet
        is then loaded into a DataFrame using the pandas.read_excel function, and the spreadsheet file is then
        deleted from the filesystem.

        Args:
            label (str): A string indicating which cycle data to download.  Valid values are "Latest" to download
                the most recent cycle data for each cluster, or "All" for all historical cycle data for each cluster.
        Returns:
            The dataframe object returned by running `pandas.read_excel(f, header=[0, 1, 2])` on the downloaded
            Excel spreadsheet.
        """
        wait = WebDriverWait(self.driver, 10)
        wait.until(find_element("a", text="Cycles")).click()
        wait.until(
            find_element("button", text=" Cycles", comparator=str.endswith)
        ).click()
        wait.until(find_element("a", text=f"{label} Cycles")).click()
        time.sleep(0.5)
        wait.until(find_element("button", name="EXPORT DATA|")).click()
        wait.until(find_element("a", text="Excel")).click()
        download_path = Path(self.download_dir.name).joinpath(f"{label} Cycles.xlsx")
        while not download_path.is_file():
            time.sleep(0.1)
        with open(download_path, "rb") as f:
            data = pandas.read_excel(f, header=[0, 1, 2])
        if self.output_dir is not None:
            shutil.copy2(download_path, self.output_dir)
        download_path.unlink()
        return data

    def get_latest_cycles(self) -> pandas.DataFrame:
        """Get the table of the latest CGP data for each cluster.

        This function will navigate to the latest cycles page, download the data in Excel format, and load it
        into a DataFrame.

        Returns:
            The dataframe object returned by running `pandas.read_excel(f, header=[0, 1, 2])` on the downloaded
            Excel spreadsheet."""
        return self._get_cycles_data("Latest")

    def get_all_cycles(self) -> pandas.DataFrame:
        """Get the table of CGP data from all available cycles for each cluster.

        This function will navigate to the all cycles page, download the data in Excel format, and load it
        into a DataFrame.

        Returns:
            The dataframe object returned by running `pandas.read_excel(f, header=[0, 1, 2])` on the downloaded
            Excel spreadsheet."""
        return self._get_cycles_data("All")

    def get_individuals_data(self) -> pandas.DataFrame:
        """Get the spreadsheet of records of individuals.

        This function will navigate to the individuals page, download the table in Excel format, and load it
        into a DataFrame.

        Returns:
            The dataframe object returned by running `pandas.read_excel(f, header=[0, 1, 2])` on the downloaded
            Excel spreadsheet."""
        wait = WebDriverWait(self.driver, 10)
        wait.until(find_element("a", text="Individuals")).click()
        wait.until(find_element("button", name="EXPORT DATA|")).click()
        wait.until(find_element("a", text="Excel")).click()
        try:
            # When downloading individual data for the whole region, there is an extra TOTP check that we have to
            # pass in to authenticate.
            auth = wait.until(
                find_element(
                    "input",
                    name="Please enter a verification code from the Google Authenticator "
                    "app on your mobile device to continue.",
                )
            )
            auth.send_keys(self.get_totp())
            wait.until(find_element("button", name="OK")).click()
        except TimeoutException:
            pass
        download_path = Path(self.download_dir.name).joinpath("All Individuals.xlsx")
        while not download_path.is_file():
            time.sleep(0.1)
        with open(download_path, "rb") as f:
            data = pandas.read_excel(f, header=[0, 1])
        download_path.unlink()
        return data

    def _get_activity_links(self) -> list:
        """Get the links to all the activities listed on the current page.

        This assumes that the SRPO object has already browsed to the Activities page.  This function will scan through
        all of the anchor elements on the page and pick out the ones that link to activities.  It makes this
        determination by checking the accessible name of the anchor element.  If the accessible name begins with the
        name of a children's class grade, a junior youth text title, or a study circle book, as defined in the lists
        initialized in this class's constructor, then it is considered a link to an activity and is included in the
        resulting list that is returned."""
        anchors = self.driver.find_elements(by=By.TAG_NAME, value="a")
        activity_links = []
        for a in anchors:
            for prefix in self.all_activity_prefixes:
                if a.accessible_name.startswith(prefix):
                    activity_links.append(a)
                    break
        return activity_links

    def _retrieve_activity(self, activity_link: WebElement) -> Activity:
        """Open an activity page and parse the activity's data into an object.

        Args:
            activity_link (WebElement): The link to click to open the activity's page.

        Return: An activity object containing the activity's data."""
        wait = WebDriverWait(self.driver, 10)
        activity_link.click()
        time.sleep(1)
        # "×" is the text of the button that closes the currently-opened activity page
        close_button = wait.until(find_element("span", text="×"))
        activity = self.parser.parse(self.driver.page_source)
        close_button.click()
        return activity

    def get_activities(self, activity: str = "All Activities") -> List[Activity]:
        """Get data on activities of a given type.

        Args:
            activity (str): String specifying the activity to retrieve data on.  Valid choices are:

                * All Activities
                * Children’s Classes
                * Junior Youth Groups
                * Study Circles

                (Note the special apostrophe used in "Children’s Classes")
        """
        valid_activities = [
            "All Activities",
            "Children’s Classes",
            "Junior Youth Groups",
            "Study Circles",
        ]
        assert activity in valid_activities
        wait = WebDriverWait(self.driver, 10)
        wait.until(find_element("a", text="Activities")).click()
        wait.until(
            find_element(
                "button",
                text=valid_activities,
                comparator=lambda text, choices: text in choices,
            )
        ).click()
        wait.until(find_element("a", text=activity)).click()
        # TODO: see if there's an element that indicates it's done loading
        time.sleep(1.5)
        activities = []
        # the selenium approach used in this script doesn't seem to be sufficient to pull table data efficiently
        # out of the page source (or maybe I just don't know how to use it properly), so we pass the page source
        # into a separate parser to pull the activity data out of it.
        next_page_button = wait.until(find_element("a", name="Next page"))
        while True:
            # This while loop iterates over the pages of data
            for link in self._get_activity_links():
                activities.append(self._retrieve_activity(link))
            if "k-state-disabled" in next_page_button.get_attribute("class"):
                # There aren't any more pages
                break
            else:
                next_page_button.click()
                time.sleep(1)
        return activities


def real_path(path: str) -> Path:
    """Helper function for arg parser to check whether a directory exists."""
    p = Path(path)
    if p.exists() and p.is_dir():
        return p
    raise NotADirectoryError(p)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-u", "--username", type=str, help="Username used to log into the SRPO website."
    )
    parser.add_argument(
        "-p", "--password", type=str, help="Password used to log into the SRPO website."
    )
    parser.add_argument(
        "-s",
        "--secret",
        type=str,
        default=None,
        help="Secret string in base-32 format that can be used to generate TOTP tokens.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=real_path,
        default=None,
        help="If this is specified, any files that were downloaded will be copied into this directory instead of "
        "deleted after being loaded.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s - %(message)s",
    )
    logging.getLogger("seleniumwire").setLevel(logging.WARNING)
    """if args.log_file is not None:
        handler = logging.FileHandler(args.log_file)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(handler)"""

    args = get_args()

    srpo = SRPO(args.secret, args.output_dir)
    srpo.login(args.username, args.password)
    # srpo.set_area("British Columbia")
    srpo.set_area("BC03 - Southeast Victoria")
    # latest_cycles = srpo.get_latest_cycles()
    # all_cycles = srpo.get_all_cycles()
    # individuals = srpo.get_individuals_data()
    # activities = srpo.get_activities("Children’s Classes")
    # activities = srpo.get_activities("Junior Youth Groups")
    # activities = srpo.get_activities("Study Circles")
    activities = srpo.get_activities("All Activities")
    srpo.cleanup()
    exit(0)  # just adding an extra line for a breakpoint
