#!/usr/bin/env python3

import argparse

from activity_parser import Activity
from srpo import real_path

# This script is used to generate blank copies of the three types of activity form.  Example invocation:
#
#    pipenv run ./gen_blank_pdfs.py -o .
#
# This will generate three PDFs in the current directory with blank forms for children's classes, junior youth
# groups, and study circles.


def get_args():
    parser = argparse.ArgumentParser(
        description="Generate blank forms for the three imperatives.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=real_path,
        required=True,
        help="The PDF files will be written to this directory.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()

    for activity_type in ["Children's Class", "Junior Youth Group", "Study Circle"]:
        blank_activity = Activity("", "", "", "", [], [], None)
        # Normally the activity determines its type based on the stage string, but we don't provide that.
        # So instead we just monkey-patch in a function that returns the desired type.  Sorry.
        blank_activity._get_activity_type = lambda: activity_type
        blank_activity.generate_pdf(
            args.output_dir.joinpath(f"{activity_type} Blank.pdf")
        )
