### Phase II Data Integration ### 

# The healthcare team needs to gather data from the EHR: analytics -> Clinical/Operational Analytics Reports -> Patient Dem Custom 
# The healthcare team also needs to manually add the city and state column from each screening event.


#load necessary packages
import numpy as np
import pandas as pd

#load the datasets
datset_clinic = pd.read_csv("EHR_clinic_data.csv")
dataset_medunderserved = pd.read_csv("MUA_DATA_2025.csv")
dataset_city_county = pd.read_csv("US_City_County_Data.csv")

# First merge: add county information to the medical data
clinic_with_county = pd.merge(datset_clinic, dataset_city_county[['City', 'State', 'County']], 
                              on=['City', 'State'], how='left')

# Second merge: add rural and medically underserved info, which is based on county
merged_data = pd.merge(clinic_with_county, 
                        dataset_medunderserved[['State', 'County', 'Rural Status Description', 'Designation Type']],
                        on=['State', 'County'], how='left')



### Phase III Data Analysis ###

#Calculate total count of precancerous, NMSC, and Melanoma diagnosis, use keywords (see below)
#Optional, for reporting we can group the lesions based on: melanoma, basal cell carcinoma, squamous cell carcinoma, precancerous lesion, uncertain suspicious lesion
#Calculate how many patients had multiple diagnoses in the same visit and provide a table with the multiple diagnoses


keywords = [
    "Actinic Cheilitis",
    "Actinic Keratoses", "Actinic Keratosis", "Diffuse Actinic Keratosis", "Pigmented Actinic Keratosis", "Hypertrophic Actinic Keratosis",
    "Disseminated Superficial Actinic Porokeratosis",
    "Atypical Nevi",
    "Clark's Nevi",
    "Dysplastic Nevi", "Dysplastic Nevus",
    "Rule-Out dysplastic Nevi", "Rule-Out dysplastic Nevus",
    "Neoplasm of uncertain", "Neoplasm of unspecified behavior",
    "Rule-Out Basal Cell Carcinoma",
    "Rule-out Lentigo Maligna",
    "Rule-out Melanoma",
    "Rule-Out Non-Melanoma Skin Cancer",
    "Rule-Out Recurrent Basal", "Rule-Out Recurrent Squamous Cell Carcinoma",
    "Rule-Out Squamous Cell Carcinoma", "in situ Squamous Cell Carcinoma", "Keratoacanthoma type Squamous Cell Carcinoma"
]

# Step 1: Filter rows that match any of the keywords in Diagnosis Name

# Use case-insensitive matching for keywords
pattern = '|'.join(keywords)
diagnosis_filtered = merged_data[merged_data['Diagnosis Name'].str.contains(pattern, case=False, na=False)]

# Step 2: Categorise diagnoses
def categorize_diagnosis(diagnosis):
    diagnosis = diagnosis.lower()
    if "melanoma" in diagnosis or "lentigo maligna" in diagnosis:
        return "Melanoma"
    elif "basal cell carcinoma" in diagnosis or "bcc" in diagnosis:
        return "Basal Cell Carcinoma"
    elif "squamous cell carcinoma" in diagnosis or "keratoacanthoma" in diagnosis:
        return "Squamous Cell Carcinoma"
    elif "actinic" in diagnosis or "porokeratosis" in diagnosis:
        return "Precancerous Lesion"
    elif "dysplastic" in diagnosis or "nevi" in diagnosis or "neoplasm" in diagnosis:
        return "Uncertain/Suspicious Lesion"
    else:
        return "Other"

diagnosis_filtered['Lesion Category'] = diagnosis_filtered['Diagnosis Name'].apply(categorize_diagnosis)

# Map lesion categories into summary groups
diagnosis_filtered['Group'] = diagnosis_filtered['Lesion Category'].replace({
    'Basal Cell Carcinoma': 'NMSC',
    'Squamous Cell Carcinoma': 'NMSC',
    'Melanoma': 'Melanoma',
    'Precancerous Lesion': 'Precancerous',
})

# Handle any unmapped categories
diagnosis_filtered['Group'].fillna('Other', inplace=True)

# Count occurrences by group
summary_counts = diagnosis_filtered['Group'].value_counts().loc[["Precancerous", "NMSC", "Melanoma"]].reset_index()
summary_counts.columns = ['Diagnosis Group', 'Count']
summary_counts

# Add percentage column
total = summary_counts['Count'].sum()
summary_counts['Percent'] = (summary_counts['Count'] / total * 100).round(2)

# Step 3: Find patients with multiple diagnoses in the same visit
multi_diag = merged_data.groupby(['Service Date', 'Patient_ID']).filter(lambda x: len(x) > 1)
multi_diag_table = multi_diag.groupby(['Service Date', 'Patient_ID'])['Diagnosis Name'].apply(list).reset_index()
multi_diag_table

# Export tables for reporting
#summary_counts.to_csv("diagnosis_summary_counts.csv", index=False)
#multi_diag_table.to_csv("multiple_diagnoses_table.csv", index=False)

# Show outputs (for debugging or interactive use)
print(summary_counts)
print(multi_diag_table)

### Phase IV Reporting Tool Development ###
# is there a way we can add a new spreadsheet of clinical data and it will add to the summary data and produce a new report?
#generate report of diagnosis based on the city
#generate report of diagnoses for all cities/events



### Phase V Visualization ###
# histogram of overall diagnoses
#histogram of diagnoses per city
#rural vs non-rural diagnoses comparison (pie chart?)

