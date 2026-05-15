import pdfplumber
import tempfile
import os

def extract_pdf_text(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    text = ""
    with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    os.remove(tmp_path)  # auto delete
    return text