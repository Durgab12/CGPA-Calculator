import re
import io
import pandas as pd
import pdfplumber
import streamlit as st

st.set_page_config(page_title="CGPA & SGPA Calculator", page_icon="🎓", layout="wide")

GRADE_POINTS = {"S": 10, "A": 9, "B": 8, "C": 7, "D": 6, "E": 4,
                "U": 0, "P": 0, "F": 0, "W": 0, "I": 0}
# IITM grade-card Term 03 exception, based on the user's stated rule:
TERM_03_COURSE_TO_SEMESTER = {"WS1301": 1, "WS1302": 2, "OB2202": 2}

st.title("🎓 CGPA & SGPA Calculator")
st.caption("Upload a grade-card PDF, review the extracted courses, and calculate term-wise SGPA and cumulative CGPA.")

st.info(
    "Grade mapping: S=10, A=9, B=8, C=7, D=6, E=4; U/P/F/W/I=0. "
    "Pass/Fail-category courses are excluded from CGPA. Please verify the extracted data before using the result."
)

def extract_pdf_text(pdf_file):
    pages = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)

def parse_courses(text):
    """
    Best-effort parser for IIT Madras-style grade cards.
    Extracts rows with: term, course code, title, credit, grade.
    Any uncertain extraction should be reviewed in the editable table.
    """
    rows = []
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    # Typical line: 01 CY1001 Chemistry I: Structure ... 10 C VG 2023
    pattern = re.compile(
        r"^\s*(\d{1,2})\s+([A-Z]{1,3}\d{3,5})\s+(.+?)\s+(\d{1,3})\s+([A-Z])\s+(?:VG|G|M|P)\s+\d{4}\s*$"
    )
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        term, code, title, credits, grade = match.groups()
        rows.append({
            "Original Term": int(term),
            "Course Code": code,
            "Course Title": title.strip(),
            "Credits": int(credits),
            "Grade": grade.upper(),
        })
    return rows

def classify_course(row):
    term = int(row["Original Term"])
    code = str(row["Course Code"]).upper().strip()
    # Explicit exception requested for grade-card Term 03.
    if term == 3 and code in TERM_03_COURSE_TO_SEMESTER:
        return f"Semester {TERM_03_COURSE_TO_SEMESTER[code]}"
    # Starting with Term 04, grade-card term maps to semester one less.
    if term >= 4:
        return f"Semester {term - 1}"
    if term == 1:
        return "Semester 1"
    if term == 2:
        return "Semester 2"
    # Remaining Term 03 course rows are treated as vacation courses.
    if term == 3:
        return "Vacation Course"
    # OB-prefixed courses outside the Term 03 exception are vacation courses.
    if code.startswith("OB"):
        return "Vacation Course"
    return f"Term {term}"

def calc_sgpa(frame):
    # Pass/Fail categories are excluded. U/W grades are included in attempted
    # credits in the denominator, but contribute zero grade points.
    # Grades S-E are successful grade-point grades; U/W are non-cleared attempts.
    valid = frame[~frame["Grade"].astype(str).str.upper().isin(["P", "F", "I"])]
    if valid.empty or valid["Credits"].sum() == 0:
        return None
    numerator = sum(float(r["Credits"]) * GRADE_POINTS.get(str(r["Grade"]).upper(), 0)
                    for _, r in valid.iterrows())
    denominator = float(valid["Credits"].sum())
    return numerator / denominator if denominator else None

def calculate(frame):
    frame = frame.copy()
    frame["Grade"] = frame["Grade"].astype(str).str.upper().str.strip()
    frame["Credits"] = pd.to_numeric(frame["Credits"], errors="coerce").fillna(0)
    frame["Grade Point"] = frame["Grade"].map(GRADE_POINTS)
    frame["Grade Point"] = frame["Grade Point"].fillna(0)
    frame["Display Group"] = frame.apply(classify_course, axis=1)

    # CGPA follows the provided grade-card definition: exclude Pass/Fail-category
    # grades, include U/W attempted credits in the denominator at 0 GP.
    eligible = frame[~frame["Grade"].isin(["P", "F", "I"])]
    total_credits = float(eligible["Credits"].sum())
    weighted_points = float((eligible["Credits"] * eligible["Grade Point"]).sum())
    cgpa = weighted_points / total_credits if total_credits else None

    groups = []
    for group, subset in frame.groupby("Display Group", sort=False):
        sgpa = calc_sgpa(subset)
        groups.append({"Semester / Category": group,
                       "Included Credits": float(subset[~subset["Grade"].isin(["P", "F", "I"])]["Credits"].sum()),
                       "SGPA": sgpa})
    summary = pd.DataFrame(groups)
    return frame, summary, cgpa, total_credits

with st.sidebar:
    st.header("Upload")
    uploaded = st.file_uploader("Grade card PDF", type=["pdf"])
    st.markdown("---")
if uploaded:
    try:
        pdf_text = extract_pdf_text(uploaded)
        parsed = parse_courses(pdf_text)
        if not parsed:
            st.warning("I couldn't automatically recognize course rows in this PDF. You can enter them manually in the table below.")
            parsed = [{"Original Term": 1, "Course Code": "", "Course Title": "", "Credits": 0, "Grade": "S"}]
        df = pd.DataFrame(parsed)
    except Exception as e:
        st.error(f"Could not read this PDF: {e}")
        df = pd.DataFrame([{"Original Term": 1, "Course Code": "", "Course Title": "", "Credits": 0, "Grade": "S"}])
else:
    st.write("### Try the calculator")
    st.write("Upload a grade card PDF from the left panel. You can also use the editable table below to test the calculation.")
    df = pd.DataFrame([
        {"Original Term": 1, "Course Code": "CY1001", "Course Title": "Example course", "Credits": 10, "Grade": "C"},
        {"Original Term": 1, "Course Code": "CY1002", "Course Title": "Example lab", "Credits": 3, "Grade": "A"},
    ])

st.subheader("1. Review / edit extracted courses")
st.caption("Check the rows carefully. Add or remove rows as needed. The assigned semester/category is calculated automatically.")
edited = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Original Term": st.column_config.NumberColumn(min_value=1, max_value=99, step=1),
        "Course Code": st.column_config.TextColumn(),
        "Course Title": st.column_config.TextColumn(),
        "Credits": st.column_config.NumberColumn(min_value=0, max_value=100, step=1),
        "Grade": st.column_config.SelectboxColumn(options=list(GRADE_POINTS.keys()), required=True),
    },
    key="courses_editor"
)

if not edited.empty:
    # Ensure stable data types and required columns
    for col in ["Original Term", "Credits"]:
        edited[col] = pd.to_numeric(edited[col], errors="coerce").fillna(0)
    edited["Course Code"] = edited["Course Code"].fillna("").astype(str)
    edited["Course Title"] = edited["Course Title"].fillna("").astype(str)
    edited["Grade"] = edited["Grade"].fillna("S").astype(str).str.upper().str.strip()
    calculated, summary, cgpa, total_credits = calculate(edited)

    st.subheader("2. Results")
    c1, c2, c3 = st.columns(3)
    c1.metric("Cumulative CGPA", f"{cgpa:.2f}" if cgpa is not None else "—")
    c2.metric("CGPA-eligible attempted credits", f"{total_credits:g}")
    c3.metric("Courses detected", len(calculated))

    st.markdown("#### SGPA by semester")
    display_summary = summary.copy()
    display_summary["SGPA"] = display_summary["SGPA"].map(lambda x: f"{x:.2f}" if x is not None else "—")
    display_summary["Included Credits"] = display_summary["Included Credits"].map(lambda x: f"{x:g}")
    st.dataframe(display_summary, use_container_width=True, hide_index=True)


    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        calculated.to_excel(writer, index=False, sheet_name="Course Details")
        summary.to_excel(writer, index=False, sheet_name="SGPA Summary")
        pd.DataFrame([{"CGPA": cgpa, "Eligible Attempted Credits": total_credits}]).to_excel(
            writer, index=False, sheet_name="CGPA"
        )
    st.download_button("Download results (Excel)", data=excel_buffer.getvalue(),
                       file_name="cgpa_sgpa_results.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("---")
st.caption("Note: This is a best-effort text-based PDF parser. Scanned/image-only grade cards need OCR support. Always verify extracted courses, grades, and credits.")
