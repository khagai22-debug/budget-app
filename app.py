import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import plotly.express as px

# הגדרות עמוד (חייב להיות ראשון)
st.set_page_config(page_title="מערכת תקציב אישי", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

CATEGORIES = [
    "עסק מוכר - סווג אוטומטית לפי מילון",
    "מזון וסופר",
    "אחזקת רכב (דלק, שטיפה, חניה)",
    "חשבונות",
    "בריאות ופארם",
    "ביטוחים",
    "חינוך ומסגרות",
    "פנאי, מסעדות וקניות",
    "תרומות וקהילה",
    "אפליקציות תשלום (דורש בירור)",
    "משיכה מקופת רכב (לא נכנס לתקציב שוטף)",
    "לא משויך"
]

BUDGET_PLAN = {
    "מזון וסופר": 3500,
    "אחזקת רכב (דלק, שטיפה, חניה)": 1200,
    "חשבונות": 1500,
    "בריאות ופארם": 400,
    "ביטוחים": 800,
    "חינוך ומסגרות": 2500,
    "פנאי, מסעדות וקניות": 1500,
    "תרומות וקהילה": 300,
    "אפליקציות תשלום (דורש בירור)": 500,
}

# עיצוב פרימיום צבעוני ומואר
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;800&display=swap');

/* רקע כללי לאפליקציה */
.stApp {
    background-color: #f4f7fc;
}

html, body, [class*="css"] {
    font-family: 'Heebo', sans-serif !important;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1200px;
    direction: rtl;
    text-align: right;
}

/* Hero Section צבעוני וחי */
.hero-box {
    background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
    color: white;
    border-radius: 24px;
    padding: 40px 30px;
    box-shadow: 0 20px 25px -5px rgba(59, 130, 246, 0.4);
    margin-bottom: 2.5rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.hero-box::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 60%);
    pointer-events: none;
}
.main-title {
    font-size: 3rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
    color: #ffffff;
    text-shadow: 0 4px 10px rgba(0,0,0,0.2);
}
.subtitle {
    color: #e0e7ff;
    font-size: 1.2rem;
    font-weight: 400;
}

/* כרטיסיות נתונים צבעוניות */
.metric-card {
    background: white;
    border-bottom: 4px solid #3b82f6;
    border-radius: 20px;
    padding: 24px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    margin-bottom: 1rem;
}
.metric-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 20px 25px -5px rgba(59, 130, 246, 0.15);
    border-bottom: 4px solid #8b5cf6;
}
.metric-label {
    color: #475569;
    font-size: 1.1rem;
    font-weight: 600;
}
.metric-value {
    font-size: 2.2rem;
    font-weight: 800;
    color: #1e293b;
    margin-top: 4px;
}

/* Container Boxes */
.section-box {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 24px;
    padding: 30px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
    height: 100%;
}

/* Tabs Styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 12px;
    background-color: #e2e8f0;
    border-radius: 16px;
    padding: 8px;
    margin-bottom: 24px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 12px;
    padding: 12px 24px;
    color: #475569;
    font-weight: 600;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
    color: white !important;
    box-shadow: 0 4px 10px rgba(79, 70, 229, 0.3);
}

/* Buttons */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: all 0.3s ease !important;
    width: 100%;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 8px 15px rgba(16, 185, 129, 0.5) !important;
    transform: translateY(-2px) !important;
}

/* Animations */
.shimmer-effect {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
    animation: shimmer 2s infinite linear;
}
@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

/* עיצוב לאזור שיוך חכם */
.smart-assign-box {
    background: linear-gradient(to right, #fffbeb, #e0e7ff);
    border: 2px
