import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="מערכת תקציב אישי", page_icon="💰", layout="centered")

# הגדרת הרשאות וחיבור לגוגל שיטס
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # שאיבת הסודות שהגדרנו ב-Streamlit Cloud
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

# פונקציה לטעינת נתונים
def load_dashboard_data(client, spreadsheet_url):
    sheet = client.open_by_url(spreadsheet_url).worksheet("דשבורד_תקציב")
    # משיכת תאים ספציפיים למאזן (לפי המבנה שיצרנו)
    # נניח ש-C2 זה ההכנסה, D3 זה סך ההוצאות, C4 זה המאזן
    income = sheet.acell('C2').value
    expenses = sheet.acell('D3').value
    balance = sheet.acell('C4').value
    return income, expenses, balance

st.title("💸 ניהול תקציב והוצאות")

# הקישור לקובץ שלך (אתה תחליף לקישור האמיתי)
SPREADSHEET_URL = st.secrets.get("spreadsheet_url", "הכנס_כאן_את_הקישור_שלך")

try:
    client = get_gspread_client()

    st.header("🛒 הוספת הוצאה חדשה")
    with st.form("add_tx_form"):
        date = st.date_input("תאריך", datetime.today())
        business = st.text_input("שם בית העסק (לדוגמה: רמי לוי, פז)")
        amount = st.number_input("סכום (₪)", min_value=0.0, step=10.0)

        # הקטגוריות
        categories = ["עסק מוכר - סווג אוטומטית לפי מילון", "מזון וסופר", "אחזקת רכב (דלק, שטיפה, חניה)", 
                     "חשבונות", "בריאות ופארם", "ביטוחים", "חינוך ומסגרות", "פנאי, מסעדות וקניות",
                     "תרומות וקהילה", "אפליקציות תשלום (דורש בירור)"]
        category = st.selectbox("סיווג (השאר ברירת מחדל אם העסק במילון)", categories)

        submitted = st.form_submit_button("שלח לתקציב")

        if submitted:
            if business and amount > 0:
                cat_val = category if category != "עסק מוכר - סווג אוטומטית לפי מילון" else ""
                # כתיבה לגיליון התנועות
                tx_sheet = client.open_by_url(SPREADSHEET_URL).worksheet("תנועות_אשראי")
                tx_sheet.append_row([date.strftime('%d/%m/%Y'), business, float(amount), cat_val])
                st.success(f"✅ ההוצאה בסך {amount} ₪ ב-{business} עודכנה בהצלחה!")
            else:
                st.error("נא להזין שם עסק וסכום גדול מאפס.")

except Exception as e:
    st.error("שגיאת התחברות למסד הנתונים. אנא ודא שהגדרת את ה-Secrets כראוי.")
    st.write(e)
