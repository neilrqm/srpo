# SRPO Access Script

This work-in-progress code is for programatically accessing certain data on the online SRP.  

## Installation

This requires that `google-chrome` or `chromium-browser` be installed on the system path.

To install Python prerequisites, install `pipenv` and run `pipenv install`.  This will create a virtual environment
with the necessary packages installed.  Run `pipenv shell` to open a shell with the prerequisites installed, or
run the scripts with `pipenv run ...`.

## Usage

* `srpo.py` - A module with code for downloading data from the SRPO.
* `activity_parser.py` - A module with classes representing activities.  Also contains code for generating PDF
    forms with info on an activity, its facilitators, and its participants.
* `gen_pdfs.py` - A script that downloads activity data for a given area and generates PDF forms for each.

Activity form PDFs are generated in separate files, one for each activity.  They can be combined with a separate
tool such as `pdfunite` (`sudo apt install poppler-utils`).  The following script shows one way to generate PDFs
containing the forms for each imperative (in this case for cluster BC03, Southeast Victoria)

```
#!/usr/bin/env bash

pipenv run ./gen_pdfs.py -u <username> -p <password> -s <secret string> -o ./activities -a BC03 -t all

pdfunite activities/*Children*.pdf cc.pdf    # combine the children's class forms into one PDF
pdfunite activities/*Junior*.pdf jy.pdf      # combine the junior youth group forms into one PDF
pdfunite activities/*Study*.pdf sc.pdf       # combine the study circle forms into one PDF
```

## Errors

Most crashes are due to timing errors, e.g. when the SRPO takes too long to load some data and a hard-coded
wait times out.  These can generally be bypassed by re-running the code.  Occasionally the SRPO class repeatedly
hangs during login.  The only workaround for this that I have found is to open a graphical Chrome window and then
close it.  After that the code should be able to log in normally.
