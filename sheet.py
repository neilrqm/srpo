import math
import pandas as pd

from google.oauth2 import service_account
from googleapiclient.discovery import build
from pathlib import Path
from typing import List


class Sheet:
    def __init__(
        self,
        sheet_id: str,
        tab_name: str,
        credential_keyfile: Path,
    ):
        """Represents a spreadsheet tab to write SRPO data to.

        Args:
            sheet_id (str): The spreadsheet's ID string taken from its URL.  For example, a URL might look like
                https://docs.google.com/spreadsheets/d/<sheet_id>/edit
            tab_name (str): The name of the tab to write to.  This is the name given to the tab in the spreadsheet,
                e.g. "Sheet1".
            credential_keyfile (Path): A path to the JSON keyfile providing credentials for accessing the spreadsheet.
                The keyfile should be for a service account with the editor role on the Google Sheets API."""
        self.sheet_id = sheet_id
        self.tab_name = tab_name
        self.credential_keyfile = credential_keyfile
        self.scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    def _get_range(self, cell_range: str):
        """Get a range of cells from the currently-configured sheet and tab.

        Args:
            cell_range (str): A range of cells to retrieve, e.g. "A1:D3"."""
        range_str = f"'{self.tab_name}'!{cell_range}"
        creds = service_account.Credentials.from_service_account_file(
            self.credential_keyfile, scopes=self.scopes
        )
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        result = (
            sheet.values().get(spreadsheetId=self.sheet_id, range=range_str).execute()
        )
        return result.get("values", [])

    def _check_sheet_format(self, signature: List[List[str]]) -> bool:
        """Check the currently selected tab against a table header signature.

        This will pull data from the sheet that should match the given signature.  The signature is a list of lists
        representing the headers expected from the sheet (or a subset thereof).  The signatures can be obtained by
        calling e.g. sheet._get_range("A1:G3") and copying the resulting list of lists.  Passing that signature
        into this function will then pull the same range from the current sheet and compare the two cell-by-cell
        to make sure they match in format and content.

        Args:
            signature (List[List[str]]): A list of lists such as one returned by self._get_range.
        Return:
            True if the signature matches the currely-configured spreadsheet both in format and content."""
        cell_range = f"A1:{chr(ord('A') + len(signature[0]) - 1)}{len(signature)}"
        values = self._get_range(cell_range)
        for i in range(0, len(signature)):
            for j in range(0, len(signature[i])):
                try:
                    if signature[i][j] != values[i][j]:
                        return False
                except IndexError:
                    return False
        return True

    def has_cgp_data(self) -> bool:
        """Check the currently configured tab against the header signature expected for CGP data (i.e. the content
        of the "Latest Cycles" and "All Cycles" exports).

        Return:
            True if the currently configured tab's headers match the expected CGP data signature."""
        # This signature matches the first six columns of the 3-row headers CGP data tables (range A1:G3)
        signature = [
            [
                "Cluster",
                "Region",
                "National Community",
                "Milestone",
                "Start Date",
                "End Date",
                "Table 1: Youth and Adults Who Have Completed Courses of the Training Institute",
            ],
            [],
            ["", "", "", "", "", "", "Book 1"],
        ]
        return self._check_sheet_format(signature)

    def update(self, data: pd.DataFrame, cell_range: str):
        """Update a spreadsheet tab with new data.

        This function doesn't check anything, it will just try to dump the dataframe content into the spreadsheet.
        If there are NaN values in the dataframe, they will be replaced with empty strings.  The dataframe's data
        should not include headers.  For example, if the dataframe is imported from an excel spreadsheet with headers
        in the first three rows (a la the cycle data), and if the spreadsheet is loaded with

            `pd.read_excel(filehandle, header=[0, 1, 2])`

        then the headers will be separated from the data properly and the resulting dataframe can be used directly.
        The cell range specified will be erased before the data are copied into the spreadsheet.

        Args:
            data (pd.DataFrame): A Pandas dataframe containing data to write to the Google spreadsheet.  The
                dataframe's values will be converted to a serializable data table using `data.to_numpy().tolist()`.
            cell_range (str): A range of cells specifying the area to write data to.  This should start after any
                headers that are already in the spreadsheet.  For cycle data, a cell range of "A4:BS" will usually
                be appropriate---the first three rows are the headers so we start copying data at row 4, and the
                data table extends from column A to column BS."""
        range_str = f"'{self.tab_name}'!{cell_range}"
        creds = service_account.Credentials.from_service_account_file(
            self.credential_keyfile, scopes=self.scopes
        )
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        values = data.to_numpy().tolist()
        # NaN values show up sometimes in the "Participants in Exp. Phase" column, we need to replace them with strings
        for row in values:
            for i in range(0, len(row)):
                if isinstance(row[i], float) and math.isnan(row[i]):
                    row[i] = ""
        body = {
            "majorDimension": "ROWS",  # indicate that we're sending a list of rows
            "range": range_str,
            "values": values,
        }
        # clear the contents of the spreadsheet (in case the new list is shorter than the old one for some reason)
        # and then enter the dataframe data.
        sheet.values().clear(spreadsheetId=self.sheet_id, range=range_str).execute()
        sheet.values().update(
            spreadsheetId=self.sheet_id,
            range=range_str,
            body=body,
            valueInputOption="USER_ENTERED",  # the spreadsheet should parse data as if a user typed them in
        ).execute()
