## Exception Handling in the Sun Bus Project

We added exception handling to the `compute_summary_counts()` method in the `DiagnosisAnalyzer` class.

### Why?

The method originally assumed that all three diagnosis groups ("Precancerous", "NMSC", and "Melanoma") would always be present. If one was missing, the code would raise a `KeyError`.

### Strategy

We now:
- Intersect expected group labels with actual ones to avoid missing keys.
- Wrap the logic in a `try/except` block.
- Return an empty DataFrame with proper headers if an error occurs.

This ensures the method works even when certain groups are missing in the filtered data.
