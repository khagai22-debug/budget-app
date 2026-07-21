
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="מערכת תקציב אישי", page_icon="💰", layout="wide")

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
]

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1200px;}
.main-title {font-size: 2.3rem; font-weight: 800; margin-bottom: 0.2rem;}
.subtitle {color: #6b7280; margin-bottom: 1.2rem;}
.metric-card {background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); border: 1px solid rgba(15,23,42,0.08); border-radius: 18px; padding: 18px 18px 10px 18px; box-shadow: 0 8px 30px rgba(15,23,42,0.06);}
.hero-box {background: linear-gradient(135deg, #0f766e 0%, #134e4a 100%); color: white; border-radius: 24px; padding: 24px; box-shadow: 0 14px 40px rgba(19,78,74,0.25); margin-bottom: 1rem;}
.section-box {background: white; border: 1px solid rgba(15,23,42,0.08); border-radius: 20px; padding: 18px; box-shadow: 0 8px 24px rgba(15,23,42,0.05);}
.small-note {color:#6b7280;font-size:0.92rem;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_data(spreadsheet_url):
    client = get_gspread_client()
    wb = client.open_by_url(spreadsheet_url)
    tx_sheet = wb.worksheet("תנועות_אשראי")
    dict_sheet = wb.worksheet("מילון_עסקים")

    tx_rows = tx_sheet.get_all_records()
    dict_rows = dict_sheet.get_all_records()

    df_tx = pd.DataFrame(tx_rows)
    df_dict = pd.DataFrame(dict_rows)

    if not df_tx.empty:
        df_tx = df_tx.rename(columns=lambda x: str(x).strip())
        if "סכום" in df_tx.columns:
            df_tx["סכום"] = pd.to_numeric(df_tx["סכום"], errors="coerce").fillna(0)
        else:
            df_tx["סכום"] = 0
        if "תאריך" in df_tx.columns:
            df_tx["תאריך_dt"] = pd.to_datetime(df_tx["תאריך"], dayfirst=True, errors="coerce")
        else:
            df_tx["תאריך_dt"] = pd.NaT

        category_col = None
        for c in df_tx.columns:
            if "שיוך" in c or "קטגור" in c:
                category_col = c
                break
        if category_col is None:
            df_tx["קטגוריה_לתצוגה"] = "לא משויך"
        else:
            df_tx["קטגוריה_לתצוגה"] = df_tx[category_col].replace("", pd.NA).fillna("לא משויך")
    else:
        df_tx = pd.DataFrame(columns=["תאריך", "שם עסק באשראי", "סכום", "קטגוריה_לתצוגה", "תאריך_dt"])

    business_names = []
    if not df_dict.empty:
        first_col = df_dict.columns[0]
        business_names = sorted([str(x).strip() for x in df_dict[first_col].dropna().tolist() if str(x).strip()])

    return df_tx, business_names

SPREADSHEET_URL = st.secrets.get("spreadsheet_url", "")

try:
    client = get_gspread_client()
    wb = client.open_by_url(SPREADSHEET_URL)
    tx_sheet = wb.worksheet("תנועות_אשראי")
    df_tx, business_names = load_data(SPREADSHEET_URL)

    st.markdown('<div class="hero-box">', unsafe_allow_html=True)
    st.markdown('<div class="main-title">💸 מערכת תקציב אישית</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle" style="color:#d1fae5; margin-bottom:0;">ניהול הוצאות בזמן אמת, חיווי תקציבי, גרפים ועסקאות אחרונות במקום אחד</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    total_spent = float(df_tx["סכום"].sum()) if not df_tx.empty else 0.0
    income_planned = 15000.0
    balance = income_planned - total_spent
    over_budget = balance < 0

    current_month = pd.Timestamp.today().month
    current_year = pd.Timestamp.today().year
    if not df_tx.empty and "תאריך_dt" in df_tx.columns:
        month_df = df_tx[(df_tx["תאריך_dt"].dt.month == current_month) & (df_tx["תאריך_dt"].dt.year == current_year)].copy()
    else:
        month_df = df_tx.copy()

    cat_summary = pd.DataFrame()
    if not month_df.empty:
        cat_summary = month_df.groupby("קטגוריה_לתצוגה", dropna=False)["סכום"].sum().reset_index().sort_values("סכום", ascending=False)

    recent_df = month_df.sort_values("תאריך_dt", ascending=False).head(8).copy() if not month_df.empty else pd.DataFrame()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("הכנסה מתוכננת", f"₪{income_planned:,.0f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("סה״כ הוצאות", f"₪{total_spent:,.0f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("יתרה נוכחית", f"₪{balance:,.0f}", delta=f"₪{balance:,.0f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("מספר עסקאות החודש", f"{len(month_df):,}")
        st.markdown('</div>', unsafe_allow_html=True)

    if over_budget:
        st.error("חרגת מהתקציב הכולל החודשי. כדאי לעצור ולבדוק את סעיפי ההוצאה הגדולים.")
    elif balance < 2000:
        st.warning("היתרה לחודש מתחילה להיות נמוכה. שווה לשים לב להוצאות פנאי ולקניות משתנות.")
    else:
        st.success("המצב התקציבי כרגע תקין.")

    left, right = st.columns([1.05, 0.95])

    with left:
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.subheader("🛒 הוספת הוצאה חדשה")
        with st.form("add_tx_form", clear_on_submit=True):
            date = st.date_input("תאריך", datetime.today())
            business = st.selectbox("שם בית העסק (אם קיים במילון)", options=[""] + business_names, index=0, help="אפשר לבחור עסק קיים כדי להימנע מהקלדה")
            business_manual = st.text_input("או הקלד בית עסק חדש")
            amount = st.number_input("סכום (₪)", min_value=0.0, step=10.0)
            category = st.selectbox("סיווג", CATEGORIES)
            note = st.text_input("הערה קצרה (אופציונלי)")
            submitted = st.form_submit_button("שלח לתקציב")

            if submitted:
                chosen_business = business_manual.strip() if business_manual.strip() else business.strip()
                if chosen_business and amount > 0:
                    cat_val = category if category != "עסק מוכר - סווג אוטומטית לפי מילון" else ""
                    tx_sheet.append_row([date.strftime('%d/%m/%Y'), chosen_business, float(amount), cat_val])
                    load_data.clear()
                    st.success(f"✅ ההוצאה בסך ₪{amount:,.0f} עבור {chosen_business} נשמרה בהצלחה")
                    if note:
                        st.info(f"הערה: {note}")
                else:
                    st.error("נא לבחור או להקליד בית עסק, ולהזין סכום גדול מאפס.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.subheader("📋 עסקאות אחרונות")
        if recent_df.empty:
            st.info("עדיין אין עסקאות להצגה.")
        else:
            display_cols = [c for c in ["תאריך", "שם עסק באשראי", "סכום", "קטגוריה_לתצוגה"] if c in recent_df.columns]
            show_df = recent_df[display_cols].copy()
            if "סכום" in show_df.columns:
                show_df["סכום"] = show_df["סכום"].map(lambda x: f"₪{x:,.0f}")
            st.dataframe(show_df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.subheader("📊 הוצאות לפי קטגוריה")
        if cat_summary.empty:
            st.info("אין עדיין נתונים לגרף.")
        else:
            chart_df = cat_summary.set_index("קטגוריה_לתצוגה")
            st.bar_chart(chart_df)
            st.caption("סיכום הוצאות החודש לפי הקטגוריה שהוזנה או סווגה אוטומטית")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.subheader("🥧 התפלגות הוצאות")
        if cat_summary.empty:
            st.info("אין עדיין נתונים לגרף עוגה.")
        else:
            fig = px.pie(cat_summary, names="קטגוריה_לתצוגה", values="סכום", hole=0.45)
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.subheader("🎯 מה נשאר לי להוציא")
        st.progress(max(0.0, min(1.0, balance / income_planned if income_planned else 0.0)))
        st.markdown(f"<div class='small-note'>נותרו בערך <b>₪{max(balance,0):,.0f}</b> מתוך תקציב חודשי של ₪{income_planned:,.0f}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error("שגיאת התחברות למסד הנתונים או ריצה. בדוק את הלוגים ב-Manage app.")
    st.write(e)
