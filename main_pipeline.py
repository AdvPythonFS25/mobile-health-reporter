'''Pipeline for Mobile Clinic Reporting Tool'''

#Import the needed libraries 
import numpy as np
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import us
import geopandas as gpd
from shapely.geometry import Point
from matplotlib.lines import Line2D

def load_data(path=""):
    # Load and stack all clinic CSVs from dedicated folder
    clinic_folder = os.path.join(path, "clinic_data")
    clinic_files = [f for f in os.listdir(clinic_folder) if f.endswith(".csv")]
    dataset_clinic = pd.concat(
        [pd.read_csv(os.path.join(clinic_folder, f)) for f in clinic_files],
        ignore_index=True
    )

    # Load the other datasets
    dataset_medunderserved = pd.read_csv(f"{path}MUA_DATA_2025.csv")
    dataset_city_county = pd.read_csv(f"{path}US_City_County_Data.csv")

    return dataset_clinic, dataset_medunderserved, dataset_city_county


# ---------------------- Merge Data ----------------------
def merge_datasets(dataset_clinic, dataset_medunderserved, dataset_city_county):
    # Merge clinic with county info
    clinic_with_county = pd.merge(
        dataset_clinic,
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


# ---------------------- Run Full Pipeline ----------------------

# Load data
path="Data/"
dataset_clinic, dataset_medunderserved, dataset_city_county = load_data(path)

# Merge datasets
merged_data = merge_datasets(dataset_clinic, dataset_medunderserved, dataset_city_county)

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
report_date = datetime.today().strftime('%d-%b-%Y')
final_report.to_csv(f"Summary_Report_{report_date}.csv", index=False)
print(final_report.head())

# ---------------------- Visualizations ----------------------

# Ensure plots directory exists
plots_dir = f"plots_{report_date}"
os.makedirs(plots_dir, exist_ok=True)
os.makedirs(f"{plots_dir}/maps", exist_ok=True)

# Create a safe copy of diagnosis_filtered for visualization
analyzer.diagnosis_filtered = analyzer.diagnosis_filtered.copy()

# Parse service date
analyzer.diagnosis_filtered['Service Date'] = pd.to_datetime(analyzer.diagnosis_filtered['Service Date'], format='%m/%d/%Y')

# 1. Diagnosis distribution by state
plt.figure(figsize=(12, 6))
# Replace state abbreviations with full names for plotting
analyzer.diagnosis_filtered['Full State Name'] = analyzer.diagnosis_filtered['State'].apply(lambda abbr: us.states.lookup(abbr).name if us.states.lookup(abbr) else abbr)
state_order = analyzer.diagnosis_filtered['Full State Name'].value_counts().index
sns.countplot(data=analyzer.diagnosis_filtered, y='Full State Name', order=state_order)
plt.title("Diagnosis Distribution by State")
plt.xlabel("Number of Diagnoses")
plt.tight_layout()
plt.savefig(f"{plots_dir}/diagnosis_by_state.png")
plt.close()

# 2. Diagnosis type by rural vs non-rural
plt.figure(figsize=(10, 6))
sns.countplot(data=analyzer.diagnosis_filtered, x='Group', hue='Is_Rural')
plt.title("Diagnosis Type by Rural vs Non-Rural")
plt.ylabel("Number of Diagnoses")
plt.xlabel("Diagnosis Type")
plt.tight_layout()
plt.savefig(f"{plots_dir}//diagnosis_type_by_rural_status.png")
plt.close()

# 3. Diagnosis type by rural vs non-rural per state
states = analyzer.diagnosis_filtered['State'].dropna().unique()
for state in states:
    state_data = analyzer.diagnosis_filtered[analyzer.diagnosis_filtered['State'] == state]
    if not state_data.empty:
        full_name = us.states.lookup(state).name if us.states.lookup(state) else state
        plt.figure(figsize=(10, 6))
        sns.countplot(data=state_data, x='Group', hue='Is_Rural')
        plt.title(f"Diagnosis Type by Rural vs Non-Rural in {full_name}")
        plt.ylabel("Number of Diagnoses")
        plt.xlabel("Diagnosis Type")
        plt.tight_layout()
        safe_state = state.replace(" ", "_").replace("/", "_")
        plt.savefig(f"{plots_dir}/diagnosis_type_by_rural_status_{safe_state}.png")
        plt.close()

# 4. Combined Map: State Choropleth + City Points
city_data = pd.read_csv(f"{path}US_City_County_Data.csv")
city_data['City'] = city_data['City'].astype(str).str.strip().str.lower()
city_data['State'] = city_data['State'].astype(str).str.strip().str.upper()

city_counts = analyzer.diagnosis_filtered.groupby(['City', 'State']).size().reset_index(name='Diagnosis Count')
city_counts['City'] = city_counts['City'].astype(str).str.strip().str.lower()
city_counts['State'] = city_counts['State'].astype(str).str.strip().str.upper()

city_geo = pd.merge(city_counts, city_data, on=['City', 'State'], how='left')

# Handle lat/lng columns
lat_col = next((col for col in city_geo.columns if col.strip().lower() in ['latitude', 'lat']), None)
lon_col = next((col for col in city_geo.columns if col.strip().lower() in ['longitude', 'lng', 'lon']), None)

if lat_col is None or lon_col is None:
    raise ValueError("Latitude and/or Longitude columns not found in the city data.")

city_geo = city_geo.dropna(subset=[lat_col, lon_col])
city_geo['geometry'] = city_geo.apply(lambda row: Point(row[lon_col], row[lat_col]), axis=1)
city_gdf = gpd.GeoDataFrame(city_geo, geometry='geometry', crs='EPSG:4326')

# Diagnosis counts by state
state_totals = analyzer.diagnosis_filtered.groupby('State').size().reset_index(name='Total Diagnoses')
state_totals['State'] = state_totals['State'].astype(str).str.upper()
state_totals['Full Name'] = state_totals['State'].apply(lambda abbr: us.states.lookup(abbr).name if us.states.lookup(abbr) else abbr)

us_states = gpd.read_file(f"{path}us-states.json")
us_states = us_states.rename(columns={"name": "Full Name"})
us_states = us_states.merge(state_totals, on="Full Name", how="left")

# Plot combined map
fig, ax = plt.subplots(figsize=(15, 10))
us_states.plot(column='Total Diagnoses', ax=ax, legend=True, cmap='OrRd', edgecolor='black')
city_gdf.plot(ax=ax, markersize=city_gdf['Diagnosis Count'], color='blue', alpha=0.6, edgecolor='k')
plt.title("US Diagnosis Distribution by State and City")
plt.axis('off')

bubble_sizes = [10, 50, 100, 250, 500]
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='City (diagnosis count)',
           markerfacecolor='blue', markeredgecolor='k', markersize=6, linestyle='None')
] + [
    Line2D([0], [0], marker='o', color='w', label=f'{size} cases',
           markerfacecolor='blue', markeredgecolor='k', markersize=np.sqrt(size), linestyle='None')
    for size in bubble_sizes
]
ax.legend(handles=legend_elements, loc='lower left')
plt.savefig(f"{plots_dir}/maps/us_diagnosis_map.png", bbox_inches="tight")
plt.close()

