import unittest
import pandas as pd
from diagnosis_analyser import DiagnosisAnalyzer  

class TestDiagnosisAnalyzer(unittest.TestCase):

    def test_summary_counts_with_all_groups(self):
        data = pd.DataFrame({
            'Diagnosis Name': ['Melanoma', 'Basal Cell Carcinoma', 'Actinic Keratosis'],
            'Group': ['Melanoma', 'NMSC', 'Precancerous'],
            'State': ['TX']*3, 'County': ['X']*3, 'City': ['Y']*3
        })
        analyzer = DiagnosisAnalyzer(data)
        analyzer.diagnosis_filtered = data
        result = analyzer.compute_summary_counts()
        self.assertEqual(len(result), 3)

    def test_summary_counts_missing_group(self):
        data = pd.DataFrame({
            'Diagnosis Name': ['Melanoma', 'Melanoma'],
            'Group': ['Melanoma', 'Melanoma'],
            'State': ['TX']*2, 'County': ['X']*2, 'City': ['Y']*2
        })
        analyzer = DiagnosisAnalyzer(data)
        analyzer.diagnosis_filtered = data
        result = analyzer.compute_summary_counts()
        self.assertEqual(result['Diagnosis Group'].tolist(), ['Melanoma'])

    def test_multiple_diagnoses_detection(self):
        data = pd.DataFrame({
            'Service Date': ['2024-01-01', '2024-01-01'],
            'Patient_ID': [1, 1],
            'Diagnosis Name': ['A', 'B'],
            'State': ['TX']*2, 'County': ['X']*2, 'City': ['Y']*2
        })
        analyzer = DiagnosisAnalyzer(data)
        result = analyzer.find_multiple_diagnoses()
        self.assertEqual(len(result), 1)

    def test_empty_diagnosis_filtered(self):
        analyzer = DiagnosisAnalyzer(pd.DataFrame())
        analyzer.diagnosis_filtered = pd.DataFrame()
        result = analyzer.compute_summary_counts()
        self.assertTrue(result.empty)

if __name__ == '__main__':
    unittest.main()
