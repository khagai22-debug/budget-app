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
    
    try:
        dict_sheet = wb.worksheet("מילון_עסקים")
        dict_rows = dict_sheet.get_all_records()
        df_dict = pd.DataFrame(dict_rows)
        business_names = []
        if not df_dict.empty:
            first_col = df_dict.columns[0]
            business_names = sorted([str(x).strip() for x in df_dict[first_col].dropna().tolist() if str(x).strip()])
    except:
        business_names = []
        df_dict = pd.DataFrame()

    tx_rows = tx_sheet.get_all_records()
    df_tx = pd.DataFrame(tx_rows)

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

    return df_tx, business_names, df_dict

def process_uploaded_excel(uploaded_file, df_dict):
    try:
        df_uploaded = pd.read_excel(uploaded_file, header=3)
        df_uploaded.columns = [str(c).strip() for c in df_uploaded.columns]
        
        if "תאריך עסקה" not in df_uploaded.columns or "סכום חיוב" not in df_uploaded.columns:
            st.error("הקובץ לא תואם למבנה המוכר של חברת האשראי (חסרות עמודות כמו 'תאריך עסקה' או 'סכום חיוב').")
            return None
            
        df_uploaded = df_uploaded.dropna(subset=["תאריך עסקה"])
        df_uploaded["תאריך_dt"] = pd.to_datetime(df_uploaded["תאריך עסקה"], format='%d-%m-%Y', errors="coerce")
        df_uploaded = df_uploaded.dropna(subset=["תאריך_dt"])
        
        df_mapped = pd.DataFrame()
        df_mapped["תאריך"] = df_uploaded["תאריך עסקה"]
        df_mapped["תאריך_dt"] = df_uploaded["תאריך_dt"]
        df_mapped["שם עסק באשראי"] = df_uploaded["שם בית העסק"].astype(str).str.strip()
        df_mapped["סכום"] = pd.to_numeric(df_uploaded["סכום חיוב"], errors="coerce").fillna(0)
        
        dict_mapping = {}
        if not df_dict.empty and len(df_dict.columns) >= 2:
            biz_col = df_dict.columns[0]
            cat_col = df_dict.columns[1]
            for _, row in df_dict.dropna(subset=[biz_col]).iterrows():
                b_name = str(row[biz_col]).strip()
                c_name = str(row[cat_col]).strip()
                if b_name:
                    dict_mapping[b_name] = c_name
                    
        def map_category(biz_name):
            biz_str = str(biz_name).strip()
            if biz_str in dict_mapping:
                return dict_mapping[biz_str]
            for k, v in dict_mapping.items():
                if k in biz_str:
                    return v
            return "לא משויך"
            
        df_mapped["קטגוריה_לתצוגה"] = df_mapped["שם עסק באשראי"].apply(map_category)
        
        return df_mapped
        
    except Exception as e:
        st.error(f"שגיאה בקריאת הקובץ: {e}")
        return None

SPREADSHEET_URL = st.secrets.get("spreadsheet_url", "")

try:
    df_tx, business_names, df_dict = load_data(SPREADSHEET_URL)
    
    st.markdown('<div class="hero-box">', unsafe_allow_html=True)
    st.markdown('<div class="main-title">💸 מערכת תקציב אישית</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle" style="color:#d1fae5; margin-bottom:0;">ניהול הוצאות בזמן אמת, חיווי תקציבי, גרפים ועסקאות אחרונות במקום אחד</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📊 דשבורד נוכחי (מתוך גוגל שיטס)", "📥 העלאת פירוט אשראי (סימולציה וניתוח)"])
    
    with tab1:
        total_spent = float(df_tx["סכום"].sum()) if not df_tx.empty else 0.0
        income_planned = sum(BUDGET_PLAN.values())
        balance = income_planned - total_spent
        over_budget = balance < 0

        current_month = pd.Timestamp.today().month
        current_year = pd.Timestamp.today().year
        if not df_tx.empty and "תאריך_dt" in df_tx.columns:
            month_df = df_tx[(df_tx["תאריך_dt"].dt.month == current_month) & (df_tx["תאריך_dt"].dt.year == current_year)].copy()
        else:
            month_df = df_tx.copy()

        recent_df = month_df.sort_values("תאריך_dt", ascending=False).head(8).copy() if not month_df.empty else pd.DataFrame()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("הכנסה מתוכננת (סך התקציבים)", f"₪{income_planned:,.0f}")
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
                        client = get_gspread_client()
                        wb = client.open_by_url(SPREADSHEET_URL)
                        tx_sheet = wb.worksheet("תנועות_אשראי")
                        tx_sheet.append_row([date.strftime('%d/%m/%Y'), chosen_business, float(amount), cat_val])
                        load_data.clear()
                        st.success(f"✅ ההוצאה בסך ₪{amount:,.0f} עבור {chosen_business} נשמרה בהצלחה")
                        if note:
                            st.info(f"הערה: {note}")
                    else:
                        st.error("נא לבחור או להקליד בית עסק, ולהזין סכום גדול מאפס.")
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
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

    with tab2:
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.subheader("📥 ניתוח פירוט חיובים מול יעדי תקציב")
        st.write("העלה קובץ אקסל כדי לראות כמה ניצלת מכל סעיף. מדדי ההתקדמות מראים את הניצול מהתקציב המתוכנן.")
        
        uploaded_file = st.file_uploader("בחר קובץ אקסל (.xlsx)", type=["xlsx"])
        
        if uploaded_file is not None:
            df_up = process_uploaded_excel(uploaded_file, df_dict)
            if df_up is not None and not df_up.empty:
                up_total = df_up["סכום"].sum()
                st.success(f"הקובץ נטען בהצלחה! סה״כ חיובים בקובץ: ₪{up_total:,.0f}")
                
                st.markdown("### 🎯 ניצול תקציב לפי קטגוריות")
                
                html_bars = '<div style="margin-top: 20px;">'
                
                # מציג בר עבור כל קטגוריה שיש לה תקציב, גם אם ההוצאה היא 0
                for cat in CATEGORIES:
                    if cat in ["עסק מוכר - סווג אוטומטית לפי מילון", "משיכה מקופת רכב (לא נכנס לתקציב שוטף)", "לא משויך"]:
                        continue
                        
                    limit = BUDGET_PLAN.get(cat, 0)
                    spent = df_up[df_up["קטגוריה_לתצוגה"] == cat]["סכום"].sum()
                    
                    if limit == 0:
                        continue
                        
                    percent = (spent / limit) * 100
                    clamped_percent = min(percent, 100)
                    
                    if percent <= 75:
                        bar_color = "#10b981"
                    elif percent <= 100:
                        bar_color = "#f59e0b"
                    else:
                        bar_color = "#ef4444"
                        
                    html_bars += f"""
                    <div style="margin-bottom: 22px; direction: rtl;">
                        <div style="display: flex; justify-content: space-between; font-size: 1rem; margin-bottom: 8px;">
                            <span style="font-weight: 700; color: #1e293b;">{cat}</span>
                            <span style="color: #64748b; font-size: 0.95rem;">
                                <strong>₪{spent:,.0f}</strong> מתוך ₪{limit:,.0f} <span style="color: {bar_color}; font-weight: bold; margin-right: 5px;">({percent:.0f}%)</span>
                            </span>
                        </div>
                        <div style="background-color: #e2e8f0; border-radius: 12px; height: 16px; width: 100%; overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);">
                            <div style="background-color: {bar_color}; height: 100%; width: {clamped_percent}%; border-radius: 12px; transition: width 0.5s ease-in-out;"></div>
                        </div>
                    </div>
                    """
                
                unassigned_spent = df_up[df_up["קטגוריה_לתצוגה"] == "לא משויך"]["סכום"].sum()
                if unassigned_spent > 0:
                    html_bars += f"""
                    <div style="margin-bottom: 22px; direction: rtl;">
                        <div style="display: flex; justify-content: space-between; font-size: 1rem; margin-bottom: 8px;">
                            <span style="font-weight: 700; color: #1e293b;">לא משויך (חורג / ללא תקציב)</span>
                            <span style="color: #ef4444; font-size: 0.95rem;">
                                סה"כ נוצל: <strong>₪{unassigned_spent:,.0f}</strong>
                            </span>
                        </div>
                        <div style="background-color: #e2e8f0; border-radius: 12px; height: 16px; width: 100%; overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);">
                            <div style="background-color: #94a3b8; height: 100%; width: 100%; border-radius: 12px;"></div>
                        </div>
                    </div>
                    """
                    
                html_bars += '</div>'
                
                st.markdown(html_bars, unsafe_allow_html=True)
                st.info("💡 **איך משנים את סכומי התקציב?** פתח את קובץ `app.py` ב־GitHub, חפש את השורה שמתחילה ב־`BUDGET_PLAN = {` ותוכל לשנות שם את המספרים עבור כל קטגוריה.")
                
                st.markdown("<hr>", unsafe_allow_html=True)
                l_col, r_col = st.columns(2)
                with l_col:
                    st.write("**עסקאות שנקלטו מהקובץ:**")
                    show_up = df_up[["תאריך", "שם עסק באשראי", "קטגוריה_לתצוגה", "סכום"]].copy()
                    show_up["סכום"] = show_up["סכום"].map(lambda x: f"₪{x:,.0f}")
                    st.dataframe(show_up, use_container_width=True, hide_index=True)
                
                with r_col:
                    st.write("**התפלגות קטגוריות מהקובץ:**")
                    up_cat = df_up.groupby("קטגוריה_לתצוגה")["סכום"].sum().reset_index().sort_values("סכום", ascending=False)
                    fig_up = px.pie(up_cat, names="קטגוריה_לתצוגה", values="סכום", hole=0.45)
                    fig_up.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360)
                    st.plotly_chart(fig_up, use_container_width=True)
                    
            elif df_up is not None and df_up.empty:
                st.warning("הקובץ נקרא בהצלחה, אך לא נמצאו בו שורות תקינות עם תאריך וסכום.")
                
        st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error("שגיאת התחברות למסד הנתונים או ריצה. בדוק את הלוגים ב-Manage app.")
    st.write(e)
