import pdfplumber
import re
import streamlit as st


# ---- STEP 1: Extract full PDF text ----
def extract_full_text(pdf_path):
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    return text


# ---- STEP 2: Split by COURSE CODE ----
def split_by_course(text):

    # Keep line breaks intact
    text = text.replace("\r", "\n")

    # Split whenever a new COURSE CODE starts
    pattern = r"(COURSE CODE\s*:\s*[A-Z0-9\-]+.*?)(?=COURSE CODE\s*:|\Z)"

    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

    course_map = {}

    for block in matches:

        code_match = re.search(
            r"COURSE CODE\s*:\s*([A-Z0-9\-]+)",
            block,
            re.IGNORECASE
        )

        if code_match:
            course_code = code_match.group(1).strip().upper()

            # Clean spacing slightly
            cleaned_block = re.sub(r"\n{3,}", "\n\n", block)

            course_map[course_code] = cleaned_block

    return course_map


# ---- STEP 3: Get syllabus for selected course ----
@st.cache_data
def get_course_syllabus(pdf_path, course_code):
    text = extract_full_text(pdf_path)
    course_map = split_by_course(text)

    course_code = course_code.strip().upper()
    if course_code in course_map:
        return course_map[course_code]
    else:
        return None