#!/usr/bin/env python3

import argparse

from activity_parser import Activity
from srpo import SRPO, real_path


# This is a script for generating PDF forms from a given cluster's activities.
# Example invocation:
#
#     pipenv run ./gen_pdfs.py -u <username> -p <password> -s <secret string> -o ./activities -a BC03 -t all
#
# This invocation will log into the SRPO with the specified *username*, *password* and two-factor *secret string*,
# switch the SRPO's area to cluster *BC03*, then download the data for *all* activities.


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
    "BC40": "Central Coast",
    "BC41": "Haida Gwaii",
}


def get_args():
    epilog_lines = ["The area codes map to clusters as follows:"]
    for k, v in valid_areas.items():
        epilog_lines.append(f"{k} - {v}")
    epilog = ", ".join(epilog_lines)
    parser = argparse.ArgumentParser(
        description="Generate forms for different activities in a given area.",
        epilog=epilog,
    )
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
    parser.add_argument(
        "-t",
        "--activity-type",
        type=str.lower,
        required=True,
        choices=("all", "cc", "jy", "sc"),
        help="The type of educational activity to generate PDFs for.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=real_path,
        required=True,
        help="The PDF files will be written to this directory.",
    )
    return parser.parse_args()


class PDFGen:
    num_activities = 0

    @staticmethod
    def activity_cb(a: Activity):
        a.generate_pdf(
            args.output_dir.joinpath(f"{PDFGen.num_activities:03} - {str(a)}.pdf")
        )

        PDFGen.num_activities += 1
        print(".", end="", flush=True)


if __name__ == "__main__":
    args = get_args()

    srpo = SRPO(args.secret, None)
    print("Logging in...")
    srpo.login(args.username, args.password)

    if args.area == "BC":
        area = "British Columbia"
    else:
        area = f"{args.area} - {valid_areas[args.area]}"
    srpo.set_area(area)

    print(f"Area set to {area}.")
    print("Generating activity PDFs...")

    PDFGen.num_activities = 0

    srpo.set_activity_cb(PDFGen.activity_cb)

    if args.activity_type == "all":
        activities = srpo.get_activities("All Activities")
    elif args.activity_type == "cc":
        activities = srpo.get_activities("Children’s Classes")
    elif args.activity_type == "jy":
        activities = srpo.get_activities("Junior Youth Groups")
    elif args.activity_type == "sc":
        activities = srpo.get_activities("Study Circles")

    print("Done.")
