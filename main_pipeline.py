'''Pipeline for Mobile Clinic Reporting Tool'''

#Import the needed libraries 
import numpy as np
import pandas as pd

# ---------------------- Load Datasets ----------------------
def load_data():
    datset_clinic = pd.read_csv("EHR_clinic_data.csv") #from mobile health team
    dataset_medunderserved = pd.read_csv("MUA_DATA_2025.csv") #from US Health Resources & Service GOV
    dataset_city_county = pd.read_csv("US_City_County_Data.csv") #from online database
    return datset_clinic, dataset_medunderserved, dataset_city_county

# ---------------------- Merge Data ----------------------
def merge_datasets(datset_clinic, dataset_medunderserved, dataset_city_county):
    # Merge clinic with county info
    clinic_with_county = pd.merge(
        datset_clinic,
        dataset_city_county[['City', 'State', 'County']],
        on=['City', 'State'],
        how='left'
    )

    #  Merge with medically underserved and rural status data
    merged = pd.merge(
        clinic_with_county,
        dataset_medunderserved[['State', 'County', 'Designation Type', 'Rural Status Description']],
        on=['State', 'County'],
        how='left'
    )

    # Create boolean flags for later use in reporting
    merged['Is_Underserved'] = merged['Rural Status Description'].notna()
    merged['Is_Rural'] = merged['Rural Status Description'].astype(str).str.strip().str.lower().eq('rural')

    # Convert to Yes/No for reporting
    merged['Is_Underserved'] = merged['Is_Underserved'].map({True: 'Yes', False: 'No'})
    merged['Is_Rural'] = merged['Is_Rural'].map({True: 'Yes', False: 'No'})

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

    def underserved_rural_summary(self):
        """Summarise diagnosis group by underserved and rural status,
        only if City, State, and County match with MUA data.
        """
        df = self.diagnosis_filtered.copy()

        # Make sure relevant columns exist
        for col in ['City', 'County', 'State', 'Designation Type', 'Rural Status']:
            if col not in df.columns:
                df[col] = None

        # Standardize key fields for comparison
        df['City'] = df['City'].astype(str).str.strip().str.lower()
        df['County'] = df['County'].astype(str).str.strip().str.lower()
        df['State'] = df['State'].astype(str).str.strip().str.upper()

        # Apply flags ONLY if City + County + State are present
        df['Has_Geographic_Match'] = df[['City', 'County', 'State']].notna().all(axis=1)

        df['Is_Underserved'] = df.apply(
            lambda row: 'Yes' if row['Has_Geographic_Match'] and pd.notna(row['Designation Type']) else 'No',
            axis=1
        )

        df['Is_Rural'] = df.apply(
            lambda row: 'Yes' if row['Has_Geographic_Match'] and isinstance(row['Rural Status'], str) and row['Rural Status'].strip().lower() == 'rural' else 'No',
            axis=1
        )

        return df.groupby(['Is_Underserved', 'Is_Rural', 'Group']).size().reset_index(name='Count')


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
underserved_summary = analyzer.underserved_rural_summary()

# Step 4: Create unified city-level summary table
def generate_city_summary(analyzer):
    data = analyzer.data
    diag_data = analyzer.diagnosis_filtered

    total_patients = data.groupby(['City', 'State']).agg({
        'Patient_ID': pd.Series.nunique
    }).rename(columns={'Patient_ID': '# patient count'}).reset_index()

    multi_diag = analyzer.find_multiple_diagnoses()
    multi_diag['Has_Multiple'] = True
    multiple_patients = multi_diag.groupby(['Service Date', 'Patient_ID']).size().reset_index()[['Patient_ID']]
    multiple_counts = data[data['Patient_ID'].isin(multiple_patients['Patient_ID'])].groupby(['City', 'State']).agg({
        'Patient_ID': pd.Series.nunique
    }).rename(columns={'Patient_ID': '# patient with multiple diagnoses'}).reset_index()

    category_counts = diag_data.groupby(['City', 'State', 'Group']).size().unstack(fill_value=0).reset_index()

    diag_data['Is_Suspicious'] = diag_data['Lesion Category'].str.contains('Uncertain|Suspicious', case=False, na=False)
    suspicious_counts = diag_data[diag_data['Is_Suspicious']].groupby(['City', 'State']).size().reset_index(name='#Uncertain/Suspicious lesion')

    rural_underserved = data.drop_duplicates(subset=['City', 'State'])[['City', 'State', 'Is_Rural', 'Is_Underserved']]

    result = total_patients
    result = result.merge(multiple_counts, on=['City', 'State'], how='left')
    result = result.merge(category_counts, on=['City', 'State'], how='left')
    result = result.merge(suspicious_counts, on=['City', 'State'], how='left')
    result = result.merge(rural_underserved, on=['City', 'State'], how='left')

    for col in ['# patient with multiple diagnoses', 'Precancerous', 'NMSC', 'Melanoma', '#Uncertain/Suspicious lesion']:
        if col in result.columns:
            result[col] = result[col].fillna(0).astype(int)

    result = result.rename(columns={
        'Precancerous': '# precancer',
        'NMSC': '# NMSC',
        'Melanoma': '# Melanoma'
    })

    return result[['City', 'State', 'Is_Rural', 'Is_Underserved',
                   '# patient count', '# patient with multiple diagnoses',
                   '# precancer', '# NMSC', '# Melanoma', '#Uncertain/Suspicious lesion']]

final_report = generate_city_summary(analyzer)

# Step 5: Export to single spreadsheet
from datetime import datetime
report_date = datetime.today().strftime('%d-%b-%Y')
final_report.to_csv(f"Summary_Report_{report_date}.csv", index=False)
print(final_report.head())
