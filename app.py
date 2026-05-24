"""
CBT AI - Clean MVP (Navigation + MCQ Review Flow)
"""

import streamlit as st
from openai import OpenAI
import json
import re
import uuid
import smtplib
import os
import base64
import time
import streamlit.components.v1 as components
import sqlite3
from datetime import datetime, timedelta
from db import init_db
from syllabus import get_course_syllabus
from utils import extract_pdf_text
from email.mime.text import MIMEText
from db import conn, cursor
from zoneinfo import ZoneInfo

BASE_URL = st.secrets["BASE_URL"]
EMAIL_SENDER = st.secrets["EMAIL_SENDER"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
query_params = st.query_params
test_id = query_params.get("test_id")

IS_STUDENT = bool(test_id)

# ============================================================
# Hide Streamlit Header
# ============================================================
st.markdown("""
<style>

/* Hide Streamlit menu */
#MainMenu {
    visibility: hidden;
}

/* Hide footer */
footer {
    visibility: hidden;
}

/* Hide header */
header {
    visibility: hidden;
}

/* Pull entire app upward */
.block-container {
    padding-top: 0rem !important;
    margin-top: -55px !important;
}

/* Hide Streamlit chrome */
header[data-testid="stHeader"] {
    display: none;
}

div[data-testid="stToolbar"] {
    display: none;
}

div[data-testid="stDecoration"] {
    display: none;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# GLOBAL STYLES — matches config.toml theme
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&display=swap');

/* ── Base resets ─────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Fira Code', monospace !important;
}

.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
    max-width: 960px !important;
}

/* ── Sidebar ─────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #0f0f1a !important;
    border-right: 1px solid #1e1e35 !important;
}

section[data-testid="stSidebar"] .stRadio label {
    font-family: 'Fira Code', monospace !important;
    font-size: 13px !important;
    color: #94a3b8 !important;
    letter-spacing: 0.03em;
    padding: 0px 0;
}

section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] input:checked + div {
    border-color: #facc15 !important;
}


/* Sidebar brand header */
.sidebar-brand {
    padding: 0.1rem 0.1rem 0.1rem;
    margin-bottom: 0.1rem;
}
.sidebar-brand .logo-line {
    font-size: 32px;
    font-weight: 600;
    color: #facc15;
    letter-spacing: 0.05em;
}
.sidebar-brand .sub-line {
    font-size: 16px;
    color: #64748b;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    
}

/* ── Buttons ─────────────────────────────────────────────── */
div.stButton > button {
    font-family: 'Fira Code', monospace !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    background: transparent !important;
    color: #e2e8f0 !important;
    border: 1px solid #2a2a45 !important;
    border-radius: 6px !important;
    padding: 8px 18px !important;
    letter-spacing: 0.04em !important;
    transition: all 0.15s ease !important;
}

div.stButton > button:hover {
    border-color: #facc15 !important;
    color: #facc15 !important;
    background: rgba(250,204,21,0.06) !important;
}

div.stButton > button:active {
    transform: scale(0.98) !important;
}

/* Primary CTA buttons (Generate / Create Test) */
div.stButton > button[kind="primary"],
div.stButton > button:has(span:contains("Generate")),
div.stButton > button:has(span:contains("Create Test")),
div.stButton > button:has(span:contains("Submit Test")) {
    background: #facc15 !important;
    color: #0c0c14 !important;
    border-color: #facc15 !important;
    font-weight: 600 !important;
}

/* ── Inputs / selects / textareas ────────────────────────── */
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] div {
    background: #13131f !important;
    border-color: #2a2a45 !important;
    color: #e2e8f0 !important;
    font-family: 'Fira Code', monospace !important;
    font-size: 13px !important;
    border-radius: 6px !important;
}

div[data-baseweb="input"] input:focus,
div[data-baseweb="textarea"] textarea:focus {
    border-color: #facc15 !important;
    box-shadow: 0 0 0 2px rgba(250,204,21,0.12) !important;
}

label[data-testid="stWidgetLabel"] p,
.stTextInput label p,
.stSelectbox label p,
.stTextArea label p,
.stFileUploader label p {
    font-size: 12px !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    margin-bottom: 4px !important;
}

/* Disabled input (Course Title) */
div[data-baseweb="input"] input:disabled {
    color: #facc15 !important;
    opacity: 1 !important;
    -webkit-text-fill-color: #facc15 !important;
}

/* ── Alerts / status ─────────────────────────────────────── */
div[data-testid="stAlert"] {
    border-radius: 6px !important;
    font-family: 'Fira Code', monospace !important;
    font-size: 13px !important;
    border-left-width: 3px !important;
}

/* ── Spinner ─────────────────────────────────────────────── */
div[data-testid="stSpinner"] > div {
    color: #facc15 !important;
}

/* ── Page title ──────────────────────────────────────────── */

.page-header {
    display: flex;
    align-items: baseline;
    gap: 12px;

    margin-bottom: 1rem;
    padding-bottom: 0.6rem;
    padding-top: 0.1rem;

    border-bottom: 1px solid #1e1e35;
}

.page-header .page-icon {
    font-size: 22px;
}

.page-header .page-title {
    font-size: 22px;
    font-weight: 600;
    color: #e2e8f0;
    letter-spacing: 0.02em;
}

.page-header .page-tag {
    font-size: 11px;
    color: #facc15;
    border: 1px solid #facc1540;
    border-radius: 4px;
    padding: 2px 8px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

/* ── Home page: course selector card ────────────────────── */
.selector-card {
    background: #13131f;
    border: 1px solid #1e1e35;
    border-radius: 10px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.5rem;
}
.selector-card .card-label {
    font-size: 11px;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.75rem;
}

.syllabus-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #4ade80;
    background: rgba(74,222,128,0.07);
    border: 1px solid rgba(74,222,128,0.2);
    border-radius: 4px;
    padding: 4px 10px;
    margin-top: 8px;
}

/* ── Review page: question cards ────────────────────────── */
.cbt-card {
    background: #13131f;
    border: 1px solid #1e1e35;
    border-radius: 10px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.25rem;
    position: relative;
}

.cbt-card:hover {
    border-color: #2a2a45;
}

.q-number {
    display: inline-block;
    background: rgba(250,204,21,0.1);
    color: #facc15;
    border: 1px solid rgba(250,204,21,0.25);
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    padding: 2px 8px;
    margin-bottom: 10px;
}

.cbt-question {
    font-size: 14px;
    line-height: 1.7;
    color: #e2e8f0;
    margin-bottom: 1rem;
}

.cbt-option {
    padding: 10px 14px;
    margin-bottom: 7px;
    border-radius: 6px;
    background: #0c0c14;
    border: 1px solid #1e1e35;
    font-size: 13px;
    color: #94a3b8;
    letter-spacing: 0.01em;
}

.cbt-option b {
    color: #475569;
    margin-right: 6px;
}

.cbt-answer {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 14px;
    padding: 10px 14px;
    border-radius: 6px;
    background: rgba(74,222,128,0.07);
    border: 1px solid rgba(74,222,128,0.2);
    font-size: 13px;
    color: #4ade80;
    font-weight: 500;
}

.divider {
    border: none;
    border-top: 1px solid #1e1e35;
    margin: 1.5rem 0;
}

/* ── Create Test page ────────────────────────────────────── */
.section-heading {
    font-size: 11px;
    color: #facc15;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.75rem;
    margin-top: 1.5rem;
}

/* ── Student test page ───────────────────────────────────── */
.timer-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #13131f;
    border: 1px solid #1e1e35;
    border-radius: 8px;
    padding: 12px 18px;
    margin-bottom: 1.5rem;
}
.timer-label {
    font-size: 11px;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.timer-value {
    font-size: 20px;
    font-weight: 600;
    color: #facc15;
    letter-spacing: 0.05em;
}

.student-q-card {
    background: #13131f;
    border: 1px solid #1e1e35;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
}

.student-q-text {
    font-size: 14px;
    line-height: 1.7;
    color: #e2e8f0;
    margin-bottom: 0.75rem;
}

/* ── Radio buttons (student test) ────────────────────────── */
div[data-testid="stRadio"] label {
    font-family: 'Fira Code', monospace !important;
    font-size: 13px !important;
    color: #94a3b8 !important;
}

/* RADIO BUTTON FIX (NO YELLOW BACKGROUND) */

div[data-testid="stRadio"] [data-baseweb="radio"] input:checked ~ div div {
    background-color: transparent !important;
    border-color: #facc15 !important;
}

/* Sidebar navigation specifically */
section[data-testid="stSidebar"] label[data-baseweb="radio"] {
    background: transparent !important;
}

/* Remove hover highlight */
section[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
    background: transparent !important;
}


/* ── Score reveal ────────────────────────────────────────── */
.score-card {
    text-align: center;
    background: #13131f;
    border: 1px solid #facc1540;
    border-radius: 12px;
    padding: 2.5rem;
    margin: 2rem auto;
    max-width: 400px;
}
.score-card .score-num {
    font-size: 56px;
    font-weight: 600;
    color: #facc15;
    line-height: 1;
}
.score-card .score-label {
    font-size: 12px;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-top: 8px;
}

/* ── Login card (student entry) ─────────────────────────── */
.login-card {
    background: #13131f;
    border: 1px solid #1e1e35;
    border-radius: 12px;
    padding: 0.2rem 0.2rem;
    max-width: 480px;
    margin-left: 0;
    margin-right: auto;
    text-align: left;
    margin-bottom: 8px;
}
.login-card .login-title {
    font-size: 18px;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 0.5px;
}
.login-card .login-sub {
    font-size: 12px;
    color: #475569;
    margin-bottom: 0.5rem;
    letter-spacing: 0.04em;
}

/* ── Test link box ───────────────────────────────────────── */
.link-box {
    background: #0c0c14;
    border: 1px solid #facc1540;
    border-radius: 6px;
    padding: 12px 16px;
    font-size: 12px;
    color: #facc15;
    word-break: break-all;
    letter-spacing: 0.02em;
}

/* ── Misc ────────────────────────────────────────────────── */
h1, h2, h3, h4 {
    font-family: 'Fira Code', monospace !important;
}

/* Hide menu + footer ONLY */
#MainMenu, footer {
    display: none !important;
}

/* Keep header visible but minimal */
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 40px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>

/* Reduce vertical gaps between blocks */
section[data-testid="stSidebar"] .block-container {
    padding-top: 5px;
}

/* Reduce markdown spacing */
section[data-testid="stSidebar"] div.stMarkdown {
    margin-bottom: 3px;
}

/* Tighten image spacing */
section[data-testid="stSidebar"] img {
    margin-bottom: 6px;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>

/* ============================================================
   🎨 PrashnaAI DESIGN SYSTEM
============================================================ */

/* ---- COLOR SYSTEM ---- */
:root {
    --bg-main: #0c0c14;
    --bg-card: #13131f;
    --bg-soft: #0f0f1a;

    --border: #1e1e35;
    --border-strong: #2a2a45;

    --text-main: #e2e8f0;
    --text-muted: #64748b;

    --accent: #facc15;
    --accent-soft: rgba(250,204,21,0.08);
}

/* ---- TYPOGRAPHY ---- */
h1, h2, h3 {
    font-weight: 600;
    letter-spacing: 0.02em;
}

h1 { font-size: 26px; }
h2 { font-size: 20px; }
h3 { font-size: 16px; }

p {
    line-height: 1.6;
}

/* ---- SPACING SYSTEM ---- */
.section {
    margin-bottom: 1.5rem;
}

.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
}

.card-tight {
    padding: 1rem;
}

/* ---- HEADER (GLOBAL FIX) ---- */
.bodha-header {
    position: relative;
    left: 50%;
    right: 50%;
    margin-left: -50vw;
    margin-right: -50vw;
    width: 100vw;

    display: flex;
    align-items: center;
    justify-content: space-between;

    padding: 7px 20px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-main);
    z-index: 999;
}

.bodha-header img {
    width: 95px;
}

.bodha-center {
    text-align: center;
    flex-grow: 1;
}

.bodha-title {
    font-size: 32px;
    font-weight: 700;
    color: var(--text-main);
    letter-spacing: 0.05em;
}

.bodha-sub {
    font-size: 12px;
    color: var(--text-muted);
    letter-spacing: 0.08em;
    margin-top: 4px;
}

/* ---- BUTTON SYSTEM (UNIFIED) ---- */
div.stButton > button {
    border-radius: 6px !important;
    border: 1px solid var(--border-strong) !important;
    background: transparent !important;
    color: var(--text-main) !important;
    padding: 6px 14px !important;
    font-size: 12px !important;
    letter-spacing: 0.04em !important;
}

div.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: var(--accent-soft) !important;
}

/* PRIMARY ACTION */
button[kind="primary"] {
    background: var(--accent) !important;
    color: #0c0c14 !important;
    border-color: var(--accent) !important;
}

/* ---- INPUT CONSISTENCY ---- */
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-main) !important;
}

/* ---- REMOVE RANDOM EMPTY STRIPS ---- */
.block-container > div:empty {
    display: none;
}

/* ---- CARD HOVER (SUBTLE) ---- */
.card:hover {
    border-color: var(--border-strong);
}

/* ---- DIVIDER CLEAN ---- */
hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 4rem 0;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# COURSE DATA DICTIONARY
# -----------------------------

COURSE_DATA = {

    "Finance Management": [
        {"code": "25MBAF001", "title": "FINANCIAL MARKETS AND SERVICES"},
        {"code": "25MBAF002", "title": "MERGERS, ACQUISITION AND RESTRUCTURING"},
        {"code": "25MBAF003", "title": "SECURITY ANALYSIS AND PORTFOLIO MANAGEMENT"},
        {"code": "25MBAF004", "title": "FINANCIAL DERIVATIVES AND RISK MANAGEMENT"},
        {"code": "25MBAF005", "title": "INTERNATIONAL FINANCIAL MANAGEMENT"},
    ],

    "Human Resource Management": [
        {"code": "25MBAH001", "title": "EMPLOYEE RELATIONS AND LABOUR LAW"},
        {"code": "25MBAH002", "title": "PERFORMANCE MANAGEMENT & COMPENSATION MANAGEMENT"},
        {"code": "25MBAH003", "title": "HIRING & PSYCHOMETRIC ASSESSMENT"},
        {"code": "25MBAH004", "title": "STRATEGIC HUMAN RESOURCE & CHANGE MANAGEMENT"},
        {"code": "25MBAH005", "title": "INTERNATIONAL HRM AND CROSS-CULTURAL MANAGEMENT"},
    ],

    "Marketing Management": [
        {"code": "25MBAM001", "title": "MODERN MARKETING"},
        {"code": "25MBAM002", "title": "RURAL MARKETING"},
        {"code": "25MBAM003", "title": "DIGITAL MARKETING"},
        {"code": "25MBAM004", "title": "INTEGRATED MARKETING COMMUNICATIONS"},
        {"code": "25MBAM005", "title": "STRATEGIC GLOBAL MARKETING & DISTRIBUTION"},
    ],

    "IT & Systems Management": [
        {"code": "25MBAI001", "title": "ENTERPRISE IT SYSTEMS AND APPLICATIONS"},
        {"code": "25MBAI002", "title": "BUSINESS TECHNOLOGIES"},
        {"code": "25MBAI003", "title": "PROGRAM AND PROJECT MANAGEMENT"},
        {"code": "25MBAI004", "title": "STARTUP AND PRODUCT DEVELOPMENT"},
        {"code": "25MBAI005", "title": "FUNDAMENTALS OF AI, ML & RPA"},
    ],

    "Supply Chain Management": [
        {"code": "25MBAS001", "title": "LOGISTICS & SUPPLY CHAIN DESIGN"},
        {"code": "25MBAS002", "title": "ADVANCE INVENTORY & WAREHOUSING MANAGEMENT"},
        {"code": "25MBAS003", "title": "PROCUREMENT & SUPPLY CHAIN PLANNING"},
        {"code": "25MBAS004", "title": "DEMAND MANAGEMENT & CUSTOMER SERVICES"},
        {"code": "25MBAS005", "title": "SUPPLY CHAIN TRANSFORMATION AND ANALYTICS"},
    ],

    "Entrepreneurship Management": [
        {"code": "25MBAE001", "title": "STARTUP THINKING AND INNOVATION STRATEGY"},
        {"code": "25MBAE002", "title": "BUSINESS PLAN DEVELOPMENT"},
        {"code": "25MBAE003", "title": "ENTREPRENEURIAL FINANCE"},
        {"code": "25MBAE004", "title": "NEW VENTURE CREATION"},
        {"code": "25MBAE005", "title": "SOCIAL ENTREPRENEURSHIP"},
    ],

    "Business Analytics": [
        {"code": "25MBAB001", "title": "DATA MANAGEMENT SYSTEMS"},
        {"code": "25MBAB002", "title": "APPLIED ANALYTICS"},
        {"code": "25MBAB003", "title": "DATA VISUALIZATION FOR DECISION MAKING"},
        {"code": "25MBAB004", "title": "PREDICTIVE ANALYTICS USING R"},
        {"code": "25MBAB005", "title": "EDA USING PYTHON"},
    ],

    "Artificial Intelligence": [
        {"code": "25MBAR001", "title": "DATA SCIENCE FUNDAMENTALS"},
        {"code": "25MBAR002", "title": "DEEP LEARNING & ADVANCED MODELS"},
        {"code": "25MBAR003", "title": "MACHINE LEARNING BASICS"},
        {"code": "25MBAR004", "title": "MANAGING AI TRANSFORMATION"},
        {"code": "25MBAR005", "title": "INDUSTRY APPLICATIONS OF AI"},
    ],

    "FinTech": [
        {"code": "25MBAT001", "title": "FINANCIAL SERVICES TECHNOLOGY"},
        {"code": "25MBAT002", "title": "BLOCKCHAIN FOR BUSINESS"},
        {"code": "25MBAT003", "title": "INNOVATIONS IN WEALTH MANAGEMENT"},
        {"code": "25MBAT004", "title": "DIGITAL PAYMENT"},
        {"code": "25MBAT005", "title": "TECHNOLOGIES IN BANKING & INSURANCE"},
    ],
}


# -----------------------------
# PAGE HEADER
# -----------------------------
def render_header():

    def get_img(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    logo = get_img("data/university_logo.png")

    html = f"""
    <style>
        body {{
            margin:0;
            background:#0c0c14;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }}

        .header {{
            display:flex;
            align-items:center;
            gap:28px;
            padding:2px 10px 16px 10px;
            border-bottom:1px solid #1e1e35;
            background:#0c0c14;
        }}

        .logo {{
            width:200px;   /* 🔥 DOUBLE SIZE */
        }}

        .title-block {{
            display:flex;
            flex-direction:column;
        }}

        .title-row {{
            display:flex;
            align-items:center;
            gap:18px;
        }}

        .app-title {{
            font-size:54px;   /* 🔥 BIG TITLE */
            font-weight:800;
            color:#e2e8f0;
            letter-spacing:0.05em;
        }}

        .tagline {{
            font-size: 16px;
            padding: 6px 14px;
            border-radius: 8px;
            background: rgba(250,204,21,0.12);
            color: #facc15;
            border: 1px solid rgba(250,204,21,0.35);
            font-weight: 500;
            letter-spacing: 0.05em;
            margin-top: 2px;   /* 👈 THIS MOVES IT DOWN */
        }}

    .sub-header {{
        font-size: 18px;
        font-weight: 700;
        font-style: italic;
        margin-top: 2px;
        letter-spacing: 0.08em;

        /* Gradient text */
        background: linear-gradient(90deg, #facc15, #fde68a);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;

        /* Glow effect */
        text-shadow:
            0 0 8px rgba(250, 204, 21, 0.6),
            0 0 18px rgba(250, 204, 21, 0.35);

        /* Slight animation feel */
        transition: all 0.3s ease;
    }}

    </style>

    <div class="header">

        <img src="data:image/png;base64,{logo}" class="logo"/>

        <div class="title-block">

            <div class="title-row">
                <div class="app-title">PrashnaAI</div>
                <div class="tagline">AI-First Quiz Platform for SCMS-PG</div>
            </div>

            <div class="sub-header">
                AI Powered Computer Based Test (CBT) for MBA Specializations
            </div>

        </div>

    </div>
    """

    components.html(html, height=120)
# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="CBT AI", layout="wide")

st.markdown("""
<style>
/* Expand main container + left-align content */
.block-container {
    max-width: 1400px !important;
    padding-left: 40px !important;
    padding-right: 40px !important;
    margin-left: 0 !important;
}

/* Kill centered layouts from earlier CSS */
.center, .centered, .main, .stApp {
    text-align: left !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# PAGE DEFINITIONS (ICONS)
# -----------------------------
PAGES = {
    "🏠 Test Generator": "🏠 Test Generator",
    "📄 Faculty Review": "📄 Faculty Review",
    "🧪 Test Notification": "🧪 Test Notification",
    "📝 Student Test": "📝 Student Test"
}

# -----------------------------
# INIT SESSION STATE
# -----------------------------
if "page" not in st.session_state:
    st.session_state.page = "🏠 Test Generator"

if "questions" not in st.session_state:
    st.session_state.questions = []

if "syllabus" not in st.session_state:
    st.session_state.syllabus = ""

# -----------------------------
# FORCE PAGE (No escape Student)
# -----------------------------

if IS_STUDENT:
    st.session_state.page = "📝 Student Test"

# -----------------------------
# NAVIGATION HELPER
# -----------------------------
def navigate_to(page):
    st.session_state.page = page
    st.rerun()

# -----------------------------
# SIDEBAR NAVIGATION (FIXED)
# -----------------------------

with st.sidebar:
    # ============================================================
    # 🧠 BRAND
    # ============================================================
    st.markdown("""
    <div class="sidebar-brand">
        <div class="logo-line">PrashnaAI</div>
        <div class="sub-line">
            AI-First Quiz Platform for SCMS-PG
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # ============================================================
    # 🧭 NAVIGATION
    # ============================================================
    st.markdown('<div class="sidebar-section-title">Navigation</div>', unsafe_allow_html=True)

    page_options = ["🏠 Test Generator", "📄 Faculty Review", "🧪 Test Notification", "📝 Student Test", "📊 Test Results"]

    selected_page = st.radio(
        "Navigation",   # 👈 give it a label
        page_options,
        index=page_options.index(st.session_state.page),
        label_visibility="collapsed"   # 👈 hide it cleanly
    )

    if selected_page != st.session_state.page:
        st.session_state.page = selected_page
        st.rerun()
    st.markdown("---")

    # ============================================================
    # 🎓 DEAN MESSAGE (FINAL CLEAN VERSION)
    # ============================================================

    st.markdown('<div class="sub-line">Dean’s Message</div>', unsafe_allow_html=True)

    # ---- FORCE HORIZONTAL LAYOUT ----
    col1, col2 = st.columns([1.3, 2], gap="small")

    with col1:
        st.image("data/dean.png", width=130)

    with col2:
        st.markdown("""
    <div style="margin-top:0.1px;
    line-height:1.3;">
    <b style="font-size:12px;">
    Prof (Capt.) A. Nagaraj Subbarao, PhD SCMS–PG, Dayananda Sagar University
    </b><br>
    </div>
    """, unsafe_allow_html=True)

    # ---- MESSAGE (PROMINENT + CLEAN) ----
    st.markdown("""
    <div style="
        margin-top:10px;
        font-size:13.5px;
        line-height:1.7;
        color:#e2e8f0;
        border-left:2px solid #facc15;
        padding-left:10px;
    ">
    AI is transforming academic excellence through intelligent and adaptive evaluation systems.
    PrashnaAI enables next-generation assessments for modern institutions.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ============================================================
    # 📞 SUPPORT
    # ============================================================
    st.markdown('<div class="sub-line">Support</div>', unsafe_allow_html=True)

    st.markdown("""
    📧 amit.sinha@dsu.edu.in  
    Please reach out if you face any issues.
    """)

   
# -----------------------------
# HARD BLOCK ANY PAGE SWITCH
# -----------------------------
if IS_STUDENT and st.session_state.page != "📝 Student Test":
    st.session_state.page = "📝 Student Test"

# -----------------------------
# HARD BLOCK IST TIME
# -----------------------------
IST = ZoneInfo("Asia/Kolkata")

def now_ist():
    return datetime.now(IST)

# -----------------------------
# OPENAI SETUP
# -----------------------------
@st.cache_resource
def get_openai_client():
    api_key = st.secrets.get("OPENAI_API_KEY", None)
    if api_key:
        return OpenAI(api_key=api_key)
    return None

def call_openai(messages, system_prompt=None):
    client = get_openai_client()
    if not client:
        return "⚠️ OpenAI API key missing"

    try:
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=full_messages,
            max_tokens=1500,
            temperature=0.7,
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# -----------------------------
# CLEAN JSON RESPONSE
# -----------------------------
def clean_json_response(text):
    text = re.sub(r"```json|```", "", text)
    match = re.search(r"\[.*\]", text, re.DOTALL)
    return match.group(0) if match else text.strip()

# -----------------------------
# GENERATE MCQs
# -----------------------------
def generate_mcqs(context, custom_prompt=""):

    system_prompt = """
    You are an expert MBA professor.

    Generate EXACTLY 10 MCQs.

    Rules:
    - 4 options per question
    - Only one correct answer
    - No descriptive answers
    - Stay within syllabus
    """

    user_prompt = f"""
    SYLLABUS:
    {context}

    ADDITIONAL INSTRUCTIONS:
    {custom_prompt}

    Output JSON ONLY:

    [
      {{
        "question": "text",
        "options": ["A","B","C","D"],
        "correct_index": 0,
        "explanation": "text"
      }}
    ]
    """

    raw = call_openai(
        [{"role": "user", "content": user_prompt}],
        system_prompt
    )

    if raw.startswith("⚠️"):
        return {"error": raw}

    try:
        cleaned = clean_json_response(raw)
        return json.loads(cleaned)
    except:
        return {"error": "Parsing failed", "raw": raw}

def generate_single_mcq(context, custom_prompt=""):

    system_prompt = """
    You are an expert MBA professor.

    Generate EXACTLY 1 MCQ.

    Rules:
    - 4 options
    - Only one correct answer
    - Stay within syllabus
    """

    user_prompt = f"""
    SYLLABUS:
    {context}

    ADDITIONAL INSTRUCTIONS:
    {custom_prompt}

    Output JSON ONLY:

    {{
      "question": "text",
      "options": ["A","B","C","D"],
      "correct_index": 0,
      "explanation": "text"
    }}
    """

    raw = call_openai(
        [{"role": "user", "content": user_prompt}],
        system_prompt
    )

    if raw.startswith("⚠️"):
        return None

    try:
        cleaned = re.sub(r"```json|```", "", raw)
        return json.loads(cleaned)
    except:
        return None
# ============================================================
# Email Test Link
# ============================================================        

def send_test_link(email_list, link):

    for email in email_list:
        body = f"""
        You have been assigned a CBT.

        Link:
        {link}

        Note:
        - Test duration: 10 minutes
        - Available only during scheduled time
        """

        send_email(email, "CBT Test", body)

def send_email(to_email, subject, body):

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        st.error(f"Email failed: {e}")

# ============================================================
# 🏠 HOME PAGE
# ============================================================
if st.session_state.page == "🏠 Test Generator":

    init_db()
    render_header()

    
    # ---- DROPDOWNS ----
    spec = st.selectbox(
        "Select Specialization",
        list(COURSE_DATA.keys())
    )

    courses = COURSE_DATA[spec]

    course_codes = [c["code"] for c in courses]

    selected_code = st.selectbox(
        "Select Course Code",
        course_codes
    )
    st.session_state.selected_code = selected_code
    course_title = next(
        c["title"] for c in courses if c["code"] == selected_code
    )

    st.text_input("Course Title", value=course_title, disabled=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ---- LOAD SYLLABUS ----
    if st.button("Load Syllabus"):
        pdf_map = {
            "Marketing Management": "data/marketing.pdf",
            "Finance Management": "data/finance.pdf",
            "Human Resource Management": "data/hr.pdf",
            "IT & Systems Management": "data/IT.pdf",
            "Supply Chain Management": "data/SCM.pdf",
            "Entrepreneurship Management": "data/Entrepreneurship.pdf",
            "Business Analytics": "data/BA.pdf",
            "Artificial Intelligence": "data/AI.pdf",
            "FinTech": "data/FinTech.pdf"
        }

        pdf_path = pdf_map[spec]
        with st.status(
        "📘 Loading syllabus...",
        expanded=False
        ) as status:

           syllabus = get_course_syllabus(
            pdf_path,
            selected_code
            )

        if syllabus:

            st.session_state.syllabus = syllabus
            st.session_state.syllabus_status = "success"

            status.update(
                label="✅ Syllabus loaded successfully",
                state="complete"
            )

        else:

            st.session_state.syllabus = None
            st.session_state.syllabus_status = "error"

            status.update(
                label="❌ Course not found",
                state="error"
            )

        # ============================================================
        # STATUS MESSAGE
        # ============================================================
        status = st.session_state.get("syllabus_status")

        if status == "success":

            st.markdown("""
            <div class="syllabus-status success-status">
                ✓ Syllabus loaded successfully
            </div>
            """, unsafe_allow_html=True)

        elif status == "error":

            st.markdown("""
            <div class="syllabus-status error-status">
                ✗ Course not found in syllabus PDF
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ---- KEEP THESE OUTSIDE BUTTON ----
    custom_prompt = st.text_area("Instructions", placeholder="e.g. Focus on application-level questions, avoid theory-only items...")

    uploaded_file = st.file_uploader("Upload Course Notes (PDF Only)", type=["pdf"])

    extra_text = ""
    if uploaded_file:
        extra_text = extract_pdf_text(uploaded_file)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- GENERATE ----
    if st.button("📄 Generate Test"):

        context = f"""
        {st.session_state.get('syllabus','')}
        {extra_text}
        """

        # STORE CONTEXT (IMPORTANT)
        st.session_state.context = context
        st.session_state.custom_prompt = custom_prompt

        if not context.strip():
            st.error("Load syllabus first")
            st.stop()

    # ========================================================
    # AI GENERATION STATUS
    # ========================================================
        with st.status(
            "📘 Generating AI-powered MCQs...",
            expanded=True
        ) as status:

            result = generate_mcqs(
                context,
                custom_prompt
            )

        if "error" in result:

            status.update(
                label="❌ Generation failed",
                state="error"
            )

            st.error(result["error"])

        else:

            st.session_state.questions = result

            status.update(
                label=f"✅ {len(result)} MCQs generated successfully",
                state="complete"
            )

            navigate_to("📄 Faculty Review")

# ============================================================
# 📄 REVIEW PAGE (FIXED UI)
# ============================================================
elif st.session_state.page == "📄 Faculty Review":

    render_header()

    st.markdown("""
    <div class="page-header">
        <span class="page-icon">📄</span>
        <span class="page-title">Review Questions</span>
        <span class="page-tag">10 Questions</span>
    </div>
    """, unsafe_allow_html=True)

    questions = st.session_state.questions

    # ---- INIT STATE ----
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = {}

    if not questions:
        st.warning("No questions generated yet")
        st.stop()

    # ============================================================
    # QUESTIONS LOOP
    # ============================================================
    import re

    def clean_text(text):
        return re.sub(r"<.*?>", "", text)

    for i, q in enumerate(questions):

        clean_q = clean_text(q["question"])

        # ---- HEADER ----
        col1, col2 = st.columns([8, 2])

        with col1:
            st.markdown(f"""
            <div class="cbt-question">
                <span class="q-number">Q {i+1:02d}</span><br>
                {clean_q}
            </div>
            """, unsafe_allow_html=True)

        with col2:
            c1, c2, c3 = st.columns(3)

            with c1:
                if st.button("✏️", key=f"edit_{i}"):
                    st.session_state.edit_mode[i] = True

            with c2:
                if st.button("💾", key=f"save_{i}"):
                    st.session_state.edit_mode[i] = False
                    st.rerun()

            with c3:
                if st.button("↺", key=f"regen_{i}"):
                    context = st.session_state.get("context", "")
                    custom_prompt = st.session_state.get("custom_prompt", "")

                    with st.spinner(""):
                        st.toast("🔄 Generating Again...")
                        new_q = generate_single_mcq(context, custom_prompt)

                        if new_q:
                            st.session_state.questions[i] = new_q
                            st.session_state.edit_mode[i] = False
                            st.rerun()

        is_editing = st.session_state.edit_mode.get(i, False)

        # ---- EDIT MODE ----
        if is_editing:

            q["question"] = st.text_area(
                "Edit Question",
                value=q["question"],
                key=f"q_edit_{i}"
            )

            new_options = []
            for idx, opt in enumerate(q["options"]):
                updated = st.text_input(
                    f"Option {chr(65+idx)}",
                    value=opt,
                    key=f"opt_{i}_{idx}"
                )
                new_options.append(updated)

            q["options"] = new_options

            q["correct_index"] = st.selectbox(
                "Correct Answer",
                options=[0,1,2,3],
                index=q["correct_index"],
                format_func=lambda x: f"{chr(65+x)}. {q['options'][x]}",
                key=f"correct_{i}"
            )

        # ---- VIEW MODE ----
        else:

            for idx, opt in enumerate(q["options"]):
                st.markdown(
                    f"""
                    <div class="cbt-option">
                        <b>{chr(65+idx)}.</b> {opt}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            correct = q["options"][q["correct_index"]]

            st.markdown(
                f"""
                <div class="cbt-answer">
                    ✓ Correct: {correct}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown('</div>', unsafe_allow_html=True)

    # ============================================================
    # ACTIONS
    # ============================================================
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col1:
        if st.button("⬅ Back"):
            navigate_to("🏠 Test Generator")

    with col3:
        if st.button("Approve Questions ✓"):
            navigate_to("🧪 Test Notification")
# ============================================================
# 🧪 CREATE TEST PAGE
# ============================================================
elif st.session_state.page == "🧪 Test Notification":
    render_header()
    st.markdown("""
    <div class="page-header">
        <span class="page-icon">🧪</span>
        <span class="page-title">Test Notification</span>
        <span class="page-tag">Schedule & Notify</span>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.questions:
        st.warning("No approved questions found")
        if st.button("Go to Home"):
            navigate_to("🏠 Test Generator")
        st.stop()

    st.markdown('<p class="section-heading">📧 Student Emails</p>', unsafe_allow_html=True)
    selected_code = st.session_state.get("selected_code")
    emails = st.text_area(
        "Enter emails (comma separated)",
        placeholder="student1@gmail.com, student2@gmail.com"
    )

    email_list = [e.strip() for e in emails.split(",") if e.strip()]

    if email_list:
        st.markdown(f'<div class="syllabus-status">✓ {len(email_list)} recipient(s) listed</div>', unsafe_allow_html=True)

    if len(email_list) > 100:
        st.error("Maximum 100 students allowed")

    st.markdown('<p class="section-heading">⏰ Schedule Test</p>', unsafe_allow_html=True)

    now = now_ist()

    test_date = st.date_input(
        "Test Date",
        value=now.date()
    )
    
    test_time = st.time_input(
        "Start Time",
        value=now.time()
    )
    
    start_time = datetime.combine(
        test_date,
        test_time,
        tzinfo=IST
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ✅ BUTTON ADDED (CRITICAL FIX)

    if st.button("🚀 Send Notification"):

        if not email_list:
            st.error("Please enter at least one email")
            st.stop()

        if "selected_code" not in st.session_state:
            st.error("Missing course selection")
            st.stop()

        selected_code = st.session_state.selected_code

        # ============================================================
        # TEST IDS + TIMING
        # ============================================================
        public_test_id = str(uuid.uuid4())

        start = start_time.replace(tzinfo=IST)
        end = start + timedelta(minutes=10)

        # ✅ REAL DB TEST ID
        db_test_id = cursor.lastrowid

        # ============================================================
        # SAVE JSON CONFIG
        # ============================================================
        test_data = {
            "test_id": public_test_id,      # UUID used in URL
            "db_test_id": db_test_id,       # INTEGER DB ID
            "subject_id": selected_code,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "questions": st.session_state.questions,
            "allowed_emails": email_list
        }
        cursor.execute("""
        INSERT INTO tests (
            public_test_id,
            subject_id,
            start_time,
            end_time,
            questions_json,
            allowed_emails_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            public_test_id,
            selected_code,
            start.isoformat(),
            end.isoformat(),
            json.dumps(st.session_state.questions),
            json.dumps(email_list)
        ))

        # ============================================================
        # TEST LINK
        # ============================================================
        link = f"{BASE_URL}?test_id={public_test_id}"

        # ============================================================
        # SEND EMAILS
        # ============================================================
        failed_emails = []

        with st.spinner("Sending emails..."):

            for email in email_list:

                body = f"""
    You have been assigned a CBT.

    Test Link:
    {link}

    Instructions:
    - Duration: 10 minutes
    - Accessible only during scheduled time
    - Use the same email ID to access the test
    """

                try:
                    send_email(email, "CBT Test Link", body)

                except Exception:
                    failed_emails.append(email)

        # ============================================================
        # STATUS
        # ============================================================
        if failed_emails:
            st.warning(
                f"Test created but emails failed for {len(failed_emails)} recipient(s)"
            )
        else:
            st.success("✅ Test Created & Emails Sent!")

        st.markdown(
            '<p class="section-heading">🔗 Test Link</p>',
            unsafe_allow_html=True
        )

        st.markdown(
            f'<div class="link-box">{link}</div>',
            unsafe_allow_html=True
        )

# ============================================================
# 📝 STUDENT TEST PAGE
# ============================================================
elif st.session_state.page == "📝 Student Test":
    render_header()
    
    # ============================================================
    # COPY-PASTE BLOCKING FOR STUDENTS
    # ============================================================
    st.markdown("""
    <style>

    /* Disable text selection */
    html, body, [class*="css"]  {
        user-select: none;
        -webkit-user-select: none;
        -ms-user-select: none;
    }

    /* Disable image drag */
    img {
        pointer-events: none;
    }

    </style>

    <script>

    // Disable right click
    document.addEventListener('contextmenu', event => event.preventDefault());

    // Disable Ctrl+C, Ctrl+U, Ctrl+S
    document.addEventListener('keydown', function(e) {

        if (e.ctrlKey &&
        (e.key === 'c' ||
            e.key === 'u' ||
            e.key === 's')) {

            e.preventDefault();
        }
    });

    </script>
    """, unsafe_allow_html=True)

    # ---- GET TEST ID FROM URL ----
    query_params = st.query_params
    test_id = query_params.get("test_id")

    if not test_id:
        st.error("Invalid test link")
        st.stop()

    # ---- Fetch TEST CONFIG ----
    cursor.execute("""
    SELECT *
    FROM tests
    WHERE public_test_id = ?
    """, (test_id,))

    test_row = cursor.fetchone()

    if not test_row:
        st.error("Invalid test link")
        st.stop()

    # ============================================================
    # LOAD TEST CONFIG
    # ============================================================

    questions = json.loads(test_row["questions_json"])

    allowed_emails = json.loads(
        test_row["allowed_emails_json"]
    )

    start_time = test_row["start_time"]
    end_time = test_row["end_time"]
    subject_id = test_row["subject_id"]

    # REAL DB TEST ID
    db_test_id = test_row["id"]

    # ---- TIME CONVERSION ----
    start_time = datetime.fromisoformat(start_time)

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=IST)

    end_time = datetime.fromisoformat(end_time)

    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=IST)

    now = now_ist()

    # ---- TIME VALIDATION ----
    if now < start_time:
        st.warning(f"⏳ Test starts at {start_time.strftime('%H:%M:%S')}")
        st.stop()

    if now > end_time:
        st.error("❌ Test link expired")
        st.stop()

    # ---- INIT SESSION STATE ----
    if "student_started" not in st.session_state:
        st.session_state.student_started = False

    if "student_answers" not in st.session_state:
        st.session_state.student_answers = []

    if "attempted_users" not in st.session_state:
        st.session_state.attempted_users = set()

    # ============================================================
    # 🚪 BEFORE START — Login card
    # ============================================================
    if not st.session_state.student_started:

        st.markdown("""
        <div class="page-header">
            <span class="page-icon">📝</span>
            <span class="page-title">Student CBT Test</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="login-card">
            <div class="login-title">
                Enter your details
            </div>
            <div class="login-sub" style="margin-top:10px;">
                Use the email address your test was sent to:
            </div>
        </div>
        """, unsafe_allow_html=True)
        email = st.text_input("Email address")

        if st.button("Start Test"):

            if not email:
                st.error("Please enter email")
                st.stop()

            email = email.strip().lower()

            allowed = [e.lower() for e in allowed_emails]

            if email not in allowed:
                st.error("❌ You are not authorized to take this test")
                st.stop()

            if email in st.session_state.attempted_users:
                st.error("You have already attempted this test")
                st.stop()

            st.session_state.student_email = email
            st.session_state.student_started = True

            st.session_state.student_answers = [None] * len(questions)

            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # ============================================================
    # 📝 TEST IN PROGRESS
    # ============================================================
    else:

        remaining = int((end_time - now_ist()).total_seconds())

        auto_submit = remaining <= 0

        mins = max(remaining, 0) // 60
        secs = max(remaining, 0) % 60

        st.markdown(f"""
        <div class="timer-bar">
            <span class="timer-label">Time Remaining</span>
            <span class="timer-value">{mins:02d}:{secs:02d}</span>
        </div>
        """, unsafe_allow_html=True)

        for i, q in enumerate(questions):

            st.markdown(f'<div class="student-q-card"><div class="q-number">Q {i+1:02d}</div><div class="student-q-text">{q["question"]}</div></div>', unsafe_allow_html=True)

            selected = st.radio(
                "Select answer",
                q["options"],
                index=None,
                key=f"student_q_{i}"
            )

            st.session_state.student_answers[i] = selected

        # ---- PREVENT EMPTY SUBMIT ----
        if None in st.session_state.student_answers and not auto_submit:
            st.warning("Please answer all questions before submitting")
            st.stop()

        # ---- SUBMIT ----
        if st.button("Submit Test") or auto_submit:

            score = 0

            for i, q in enumerate(questions):
                selected = st.session_state.student_answers[i]

                if selected == q["options"][q["correct_index"]]:
                    score += 1

            total = len(questions)

            st.markdown(f"""
            <div class="score-card">
                <div class="score-num">{score}/{total}</div>
                <div class="score-label">Your Score</div>
            </div>
            """, unsafe_allow_html=True)
            
            # ---- GET DB TEST ID FROM JSON ----
            if not db_test_id:
                st.error("Test configuration error: Missing DB test ID")
                st.stop()

            # ---- STORE RESULT ----
            try:
                cursor.execute("""
                INSERT INTO results (
                    test_id,
                    student_email,
                    score,
                    total,
                    answers,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    db_test_id,
                    st.session_state.student_email,
                    score,
                    total,
                    json.dumps(st.session_state.student_answers),
                    now_ist().isoformat()
                ))

                conn.commit()

            except sqlite3.IntegrityError:
                st.error("⚠️ Test already submitted")
                st.stop()

            # ---- AI FEEDBACK ----
            feedback_prompt = f"""
            Student scored {score}/{total}.
            Give 2 short feedback lines.
            """

            feedback = call_openai(
                [{"role": "user", "content": feedback_prompt}]
            )

            st.info(feedback)

            # ---- LOCK USER ----
            st.session_state.attempted_users.add(
                st.session_state.student_email
            )

            st.session_state.student_started = False

            st.session_state.test_completed = True

        # ---- AFTER SUBMIT ----
        if st.session_state.get("test_completed"):
            st.success("Test submitted successfully")

            if st.button("Exit"):
                st.session_state.clear()
                st.rerun()

# ============================================================
# 📊 RESULTS PAGE (NEW FLOW)
# ============================================================
elif st.session_state.page == "📊 Test Results":

    import pandas as pd
    import json
    from datetime import datetime, timedelta
    from io import BytesIO
    from db import cursor

    st.title("📊 Test Results")

    # ============================================================
    # 🎯 SAME DROPDOWNS AS HOME PAGE
    # ============================================================
    spec = st.selectbox(
        "Select Specialization",
        list(COURSE_DATA.keys())
    )

    courses = COURSE_DATA[spec]

    course_codes = [c["code"] for c in courses]

    selected_code = st.selectbox(
        "Select Course Code",
        course_codes
    )

    course_title = next(
        c["title"] for c in courses if c["code"] == selected_code
    )

    st.text_input("Course Title", value=course_title, disabled=True)

    # ============================================================
    # 🔘 FETCH BUTTON
    # ============================================================

    if st.button("📊 Get Results"):

        # ============================================================
        # 🔍 GET LATEST TEST FOR THIS COURSE
        # ============================================================

        cursor.execute("""
        SELECT *
        FROM tests
        WHERE subject_id = ?
        ORDER BY start_time DESC
        """, (selected_code,))

        tests = cursor.fetchall()

        if not tests:
            st.warning("No tests found for this course")
            st.stop()

        latest_valid_test = None

        for test in tests:

            end_dt = datetime.fromisoformat(
                test["end_time"]
            )

            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=IST)

            if now_ist() <= end_dt + timedelta(hours=24):
                latest_valid_test = test
                break

        if not latest_valid_test:
            st.error("❌ No test found in last 24 hours")
            st.stop()

        # ============================================================
        # TEST DETAILS
        # ============================================================

        test_id = latest_valid_test["id"]

       # st.success(
       #     f"Showing results for Test ID: {test_id}"
        # )

        # ============================================================
        # LOAD QUESTIONS FROM DB
        # ============================================================

        questions = json.loads(
            latest_valid_test["questions_json"]
        )

        # ============================================================
        # FETCH STUDENT RESULTS
        # ============================================================

        cursor.execute("""
        SELECT *
        FROM results
        WHERE test_id = ?
        """, (test_id,))

        rows = cursor.fetchall()

        if not rows:
            st.warning("No student submissions found")
            st.stop()

        # ============================================================
        # BUILD DATAFRAME
        # ============================================================

        data = []

        for row in rows:

            answers = json.loads(row["answers"])

            record = {
                "Email": row["student_email"],
                "Course Code": selected_code,
                "Course Title": course_title,
                "Score": f"{row['score']}/{row['total']}",
                "Timestamp": row["timestamp"]
            }

            # ========================================================
            # QUESTION-WISE MARKS
            # ========================================================

            for i, ans in enumerate(answers):

                correct_option = questions[i]["options"][
                    questions[i]["correct_index"]
                ]

                mark = 1 if ans == correct_option else 0

                record[f"Q{i+1}"] = mark

            data.append(record)

        # ============================================================
        # DATAFRAME
        # ============================================================

        df = pd.DataFrame(data)

        st.success(
            f"{len(df)} students attempted the last test for this course"
        )

        st.dataframe(df, use_container_width=True)

        # ============================================================
        # DOWNLOAD EXCEL
        # ============================================================

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            df.to_excel(writer, index=False)

        st.download_button(
            "📥 Download Results (Excel)",
            data=output.getvalue(),
            file_name=f"results_{selected_code}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
