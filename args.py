from argparse import ArgumentParser
from pathlib import Path

valid_areas = {
    "BC": "British Columbia",
    "BC01": "Sooke",
    "BC02": "West Shore",
    "BC03": "Southeast Victoria",
    "BC04": "Saanich Peninsula",
    "BC05": "Gulf Islands",
    "BC06": "Cowichan Valley",
    "BC07": "Mid-Island",
    "BC08": "Pacific Rim Oceanside",
    "BC10": "Comox Valley",
    "BC11": "Strathcona",
    "BC13": "Vancouver",
    "BC14": "Surrey-Delta-White Rock",
    "BC15": "North Shore",
    "BC16": "Squamish-Pemberton",
    "BC17": "Sunshine Coast",
    "BC18": "Langley",
    "BC19": "Tri-Cities",
    "BC20": "Golden Ears",
    "BC21": "Abbotsford Mission",
    "BC22": "Hope Chilliwack",
    "BC23": "South Okanagan",
    "BC24": "Central Okanagan",
    "BC25": "North Okanagan",
    "BC26": "Lower Thompson-Nicola",
    "BC27": "Upper Thompson-Nicola",
    "BC28": "Columbia-Shuswap",
    "BC29": "Upper Columbia",
    "BC30": "East Kootenay",
    "BC31": "West Kootenay",
    "BC32": "Boundary",
    "BC33": "Chilcotin-Cariboo",
    "BC34": "Cariboo North",
    "BC35": "Central Interior",
    "BC36": "Northern Rockies",
    "BC37": "Kitimat Stikine",
    "BC38": "Bulkely Nechako",
    "BC39": "North Coast",
    "BC41": "Haida Gwaii",
}


def get_area_code_epilog() -> str:
    """Get an epilog string suitable for instantiating the argument parser with a list of valid areas."""
    epilog_items = ["The area codes map to clusters as follows:"]
    for k, v in valid_areas.items():
        epilog_items.append(f"{k} - {v}")
    return ", ".join(epilog_items)


def get_area_string(area_code: str) -> str:
    """Convert an area code into the full area string.

    This will take an area code and generate a string corresponding to the area selection element
    in the SRPO.  For example, given an area code "BC01", this will return the string "BC01 - Sooke", which matches
    the text of the element that needs to be clicked on in the SRPO to navigate to the Sooke cluster's data.  As a
    special case, the area code "BC" can be used to select all of British Columbia.  This value is suitable to pass
    into the SRPO.set_area function.

    Args:
        area_code (str): the 4-character cluster code (e.g. BC01) or "BC" to select the whole region.
    Return:
        The string used by the SRPO to select the given area, in the format "<code> - <cluster name>" for a cluster
        or simply "British Columbia" for the whole region."""
    if area_code == "BC":
        return "British Columbia"
    else:
        return f"{area_code} - {valid_areas[area_code]}"


def add_srpo_config(parser: ArgumentParser) -> ArgumentParser:
    """Add arguments needed for configuring the SRPO.

    Adds parameters for username, password, two-factor secret string, and area.  Uses the '-u', '-p', '-s', and '-a'
    arguments.

    Args:
        parser (ArgumentParser): the parser to add arguments to.
    Return:
        The parser object with the SRPO arguments added."""
    parser.add_argument(
        "-u",
        "--username",
        type=str,
        required=True,
        help="Username used to log into the SRPO website.",
    )
    parser.add_argument(
        "-p",
        "--password",
        type=str,
        required=True,
        help="Password used to log into the SRPO website.",
    )
    parser.add_argument(
        "-s",
        "--secret",
        type=str,
        required=True,
        help="Secret string in base-32 format that can be used to generate TOTP tokens.",
    )
    parser.add_argument(
        "-a",
        "--area",
        type=str,
        choices=list(valid_areas.keys()),
        required=True,
        help="The scope of data to retrieve.  Set to 'BC' for the region, or the 4-character "
        "code for a cluster, e.g. 'BC03' for Southeast Victoria.",
    )
    return parser


def add_sheets_config(parser: ArgumentParser) -> ArgumentParser:
    """Add arguments needed for configuring the Google Sheets API.

    Adds parameters for sheet ID, tab name, and path to the API key.

    Args:
        parser (ArgumentParser): the parser to add arguments to.
    Return:
        The parser object with the sheets arguments added."""

    parser.add_argument(
        "-i",
        "--sheet-id",
        type=str,
        required=True,
        help="Sheet ID string from the sheet's URL.",
    )
    parser.add_argument(
        "-t",
        "--tab-name",
        type=str,
        required=True,
        help=(
            "Name of the tab to write data to.  This tab must exist in the given sheet and must have the correct "
            "header format"
        ),
    )
    parser.add_argument(
        "-k",
        "--key-path",
        type=Path,
        default="sheets-editor-key.json",
        help="Path to the JSON keyfile for a service account that has edit access to the given sheet.",
    )
    return parser
