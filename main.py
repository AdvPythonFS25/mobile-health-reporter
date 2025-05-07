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

