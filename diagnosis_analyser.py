### Phase II & III: Data Integration and Analysis with Class Abstraction ###

import numpy as np
import pandas as pd

# ---------------------- Load Datasets ----------------------
def load_data():
    datset_clinic = pd.read_csv("EHR_clinic_data.csv")
    dataset_medunderserved = pd.read_csv("MUA_DATA_2025.csv")
    dataset_city_county = pd.read_csv("US_City_County_Data.csv")
    return datset_clinic, dataset_medunderserved, dataset_city_county

# ---------------------- Merge Data ----------------------
def merge_datasets(datset_clinic, dataset_medunderserved, dataset_city_county):
    clinic_with_county = pd.merge(datset_clinic, dataset_city_county[['City', 'State', 'County']],
                                  on=['City', 'State'], how='left')
    merged = pd.merge(clinic_with_county,
                      dataset_medunderserved[['State', 'County', 'Rural Status Description', 'Designation Type']],
                      on=['State', 'County'], how='left')
    return merged

# ---------------------- Class: DiagnosisAnalyzer ----------------------
class DiagnosisAnalyzer:
    def __init__(self, merged_data):
        self.data = merged_data.copy()
        self.diagnosis_filtered = None

    def filter_by_keywords(self, keywords):
        """Filter diagnoses based on keywords."""
        pattern = '|'.join(keywords)
        self.diagnosis_filtered = self.data[self.data['Diagnosis Name'].str.contains(pattern, case=False, na=False)]

    def categorize_diagnosis(self):
        """Categorize filtered diagnoses into groups."""
        def get_category(diagnosis):
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

        self.diagnosis_filtered['Lesion Category'] = self.diagnosis_filtered['Diagnosis Name'].apply(get_category)

        self.diagnosis_filtered['Group'] = self.diagnosis_filtered['Lesion Category'].replace({
            'Basal Cell Carcinoma': 'NMSC',
            'Squamous Cell Carcinoma': 'NMSC',
            'Melanoma': 'Melanoma',
            'Precancerous Lesion': 'Precancerous',
        })

        self.diagnosis_filtered['Group'].fillna('Other', inplace=True)

    def compute_summary_counts(self):
        """Count diagnoses by group with percentages."""
        try:
            counts = self.diagnosis_filtered['Group'].value_counts()
            expected_groups = ["Precancerous", "NMSC", "Melanoma"]
            summary = counts.loc[counts.index.intersection(expected_groups)].reset_index()
            summary.columns = ['Diagnosis Group', 'Count']
            total = summary['Count'].sum()
            summary['Percent'] = (summary['Count'] / total * 100).round(2)
            return summary
        except Exception as e:
            print(f"Error in computing summary counts: {e}")
            return pd.DataFrame(columns=["Diagnosis Group", "Count", "Percent"])

    def find_multiple_diagnoses(self):
        """Identify patients with multiple diagnoses in one visit."""
        multi = self.data.groupby(['Service Date', 'Patient_ID']).filter(lambda x: len(x) > 1)
        return multi.groupby(['Service Date', 'Patient_ID'])['Diagnosis Name'].apply(list).reset_index()

    def geographic_summary(self):
        """Summarise diagnoses by location."""
        geo_counts = self.diagnosis_filtered.groupby(['State', 'County', 'City', 'Group']).size().reset_index(name='Count')
        geo_total = self.diagnosis_filtered.groupby(['State', 'County', 'City']).size().reset_index(name='Total Diagnoses')
        return geo_counts, geo_total

    def underserved_summary(self):
        """Summarise diagnosis group by underserved status."""
        self.diagnosis_filtered['Is_Underserved'] = self.diagnosis_filtered['Designation Type'].notna()
        return self.diagnosis_filtered.groupby(['Is_Underserved', 'Group']).size().reset_index(name='Count')

# ---------------------- Run Full Pipeline ----------------------
# Load data
datset_clinic, dataset_medunderserved, dataset_city_county = load_data()

# Merge datasets
merged_data = merge_datasets(datset_clinic, dataset_medunderserved, dataset_city_county)

# Analyse
analyzer = DiagnosisAnalyzer(merged_data)

# Step 1: Filter by keywords
keywords = [
    "Actinic Cheilitis", "Actinic Keratoses", "Actinic Keratosis", "Diffuse Actinic Keratosis",
    "Pigmented Actinic Keratosis", "Hypertrophic Actinic Keratosis", "Disseminated Superficial Actinic Porokeratosis",
    "Atypical Nevi", "Clark's Nevi", "Dysplastic Nevi", "Dysplastic Nevus", "Rule-Out dysplastic Nevi",
    "Rule-Out dysplastic Nevus", "Neoplasm of uncertain", "Neoplasm of unspecified behavior",
    "Rule-Out Basal Cell Carcinoma", "Rule-out Lentigo Maligna", "Rule-out Melanoma",
    "Rule-Out Non-Melanoma Skin Cancer", "Rule-Out Recurrent Basal", "Rule-Out Recurrent Squamous Cell Carcinoma",
    "Rule-Out Squamous Cell Carcinoma", "in situ Squamous Cell Carcinoma", "Keratoacanthoma type Squamous Cell Carcinoma"
]
analyzer.filter_by_keywords(keywords)

# Step 2: Categorise diagnosis
analyzer.categorize_diagnosis()

# Step 3: Summaries
summary_counts = analyzer.compute_summary_counts()
multi_diag_table = analyzer.find_multiple_diagnoses()
geo_counts, geo_total = analyzer.geographic_summary()
underserved_summary = analyzer.underserved_summary()

# Step 4: Show Outputs
print(summary_counts)
print(multi_diag_table)
print(geo_counts)
print(geo_total)
print(underserved_summary)

# Export tables for reporting
summary_counts.to_csv("diagnosis_summary_counts.csv", index=False)
multi_diag_table.to_csv("multiple_diagnoses_table.csv", index=False)
geo_counts.to_csv("Geographic Hotspots and Diagnosis group ")
geo_total.to_csv("Total Diagnoses per City")
underserved_summary.to_csv("Underserved Areas vs Diagnosis Rate", index=False)
