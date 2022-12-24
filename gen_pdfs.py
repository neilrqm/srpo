#!/usr/bin/env python3

import argparse

from activity_parser import Activity
from args import get_area_code_epilog, add_srpo_config, get_area_string
from srpo import SRPO, real_path


# This is a script for generating PDF forms from a given cluster's activities.
# Example invocation:
#
#     pipenv run ./gen_pdfs.py -u <username> -p <password> -s <secret string> -o ./activities -a BC03 -t all
#
# This invocation will log into the SRPO with the specified *username*, *password* and two-factor *secret string*,
# switch the SRPO's area to cluster *BC03*, then download the data for *all* activities.


def get_args():
    parser = argparse.ArgumentParser(
        description="Generate forms for different activities in a given area.",
        epilog=get_area_code_epilog(),
    )
    add_srpo_config(parser)
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
    srpo.set_area(get_area_string(args.area))

    print(f"Area set to {get_area_string(args.area)}.")
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
