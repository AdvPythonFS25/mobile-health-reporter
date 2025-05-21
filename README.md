# mobile-clinic-reporter
The Sun Bus is a non-profit mobile dermatology clinic providing free cancer screenings across various US cities. Our project aims to build a reporting tool that helps The Sun Bus analyse screening data, identify trends in diagnoses and generate both city-specific and cumulative reports. 

# Objectives
Correlate screening events (city) with county-level data and rural/urban classification (using MUI).

Generate the following statistics:
Number of suspicious lesions diagnosed,
Distribution of cases by region and rurality,
Patients with multiple diagnoses,
Allow continuous integration of new screening event data,
Produce individual city reports and an evolving cumulative summary,
Provide data visualisations for trends over time and geography.

# Datasets
EHR data: patient demographics, visit date, diagnosis information. The data has been generated based off of patient-anonymized data collected by The Sun Bus. 
City-county mapping: US cities and their corresponding counties (from: https://simplemaps.com/data/us-cities).
Medically Underserved Index (MUI): rural/urban classification by county (from: https://data.hrsa.gov/tools/data-explorer).
Tools: Python, GitHub for version control, Markdown for documentation

# Target Users
Sun Bus Team (healthcare providers and analysts who require streamlined and up-to-date reports from mobile dermatology screenings), as well as other mobile clinics who can modify and use the tool for their benefit. 

# What you need to run this program

Option 1: Launch with binder
In order to run the program directly from your browser no prerequisites are required on your local machine. Click on the button then from after the program loads in the buit in file browser find the binder_launcher notebook and run the cell in order to execute the program. The output files are not saved but may be downloaded manually.

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/AdvPythonFS25/mobile-health-reporter.git/HEAD?urlpath=%2Fdoc%2Ftree%2Fmain_pipeline.py)

Option 2: Running on your local machine
Any code interpreter that supports python
Python installed (version 3.7+ recommended).
The required CSV files (found in data):
  EHR_clinic_data.csv
  MUA_DATA_2025.csv
  US_City_County_Data.csv
The required libraries. which are listed in the requirements.txt file
Instructions: Simply run the main_pipeline.py in your code interpreter the "Summary_Report" spreadsheet will be saved in the same directory as the executed script and the charts and maps will be saved saved in the generated "plots" directory. 

# Authors
Refer to member.txt file.


