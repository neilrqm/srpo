#!/usr/bin/env python3

import argparse

from args import (
    get_area_code_epilog,
    add_srpo_config,
    add_sheets_config,
    get_area_string,
)
from sheet import Sheet
from srpo import SRPO


def get_args():
    parser = argparse.ArgumentParser(
        description="Update online spreadsheets with latest SRPO data",
        epilog=get_area_code_epilog(),
    )
    add_srpo_config(parser)
    add_sheets_config(parser)

    parser.add_argument(
        "--type",
        required=True,
        type=str,
        choices=["latestcycles", "allcycles", "individuals"],
        help="What type of data to import from the SRPO into the spreadsheet",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()

    sheet = Sheet(args.sheet_id, args.tab_name, args.key_path)

    srpo = SRPO(args.secret, None)
    print("Logging into SRPO...", end="", flush=True)
    srpo.login(args.username, args.password)
    srpo.set_area(get_area_string(args.area))
    print(" Done", flush=True)

    print("Retrieving data from SRPO...", end="", flush=True)
    if args.type == "latestcycles":
        data = srpo.get_latest_cycles()
        cell_range = "A4:BS"
        if not sheet.has_cgp_data():
            print("Spreadsheet tab is not correctly formatted with CGP data.")
            exit(1)
    elif args.type == "allcycles":
        data = srpo.get_all_cycles()
        cell_range = "A4:BS"
        if not sheet.has_cgp_data():
            print("Spreadsheet tab is not correctly formatted with CGP data.")
            exit(1)
    elif args.type == "individuals":
        data = srpo.get_individuals_data()
        cell_range = "A3:BZ"
        if not sheet.has_individual_data():
            print(
                "Spreadsheet tab is not correctly formatted with individual record data."
            )
            exit(1)
    srpo.cleanup()

    print(" Done", flush=True)

    print("Updating sheet...", end="", flush=True)
    sheet.update(data, cell_range)
    print(" Done", flush=True)
