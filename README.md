# CGPA-Calculator
Helps Calculate CGPA and SGPA for IITM students 

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Calculation rules currently encoded

- Grade points: S=10, A=9, B=8, C=7, D=6, E=4; U/P/F/W/I=0.
- P, F, and I grades are excluded from CGPA as Pass/Fail category grades.
- U and W contribute zero grade points while their credits remain in the attempted-credit denominator, matching the uploaded grade-card note.
- Term 01 → Semester 1; Term 02 → Semester 2.
- Term 03 special mapping: WS1301 → Semester 1; WS1302 and OB2202 → Semester 2.
- Term 04 onward → Semester (original term − 1).
- Other Term 03 courses are displayed as vacation courses.
- Other OB-prefixed courses are categorized as vacation courses.

## Important

The PDF extraction is a best-effort parser for text-based grade cards. The app shows an editable table so users can correct extraction issues. Image-only/scanned PDFs need OCR support (for example, Tesseract) to be added. Do not assume the parser will recognize every university's layout.

The provided grade-card note says that Pass/Fail category courses are excluded from CGPA. Confirm how your institute treats edge cases and update `calc_sgpa()` / `calculate()` if its official policy differs.



