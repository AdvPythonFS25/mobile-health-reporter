# Changes

1. **Class `DiagnosisAnalyzer` added** to perform data filtering, categorisation, and analysis.

2. **Abstraction and Decomposition**:
   - Repeated logic was moved into class methods and functions.
   - Functions created for loading and merging datasets.
   - Each part of the analysis is modular and reusable.

## Why these changes help
- Logical blocks are named and separated clearly.
- The class can be reused with different datasets or keywords.
- Each method can be tested independently.
