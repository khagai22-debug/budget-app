import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import plotly.express as px

# הגדרות עמוד
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
</style>
""", unsafe_allow_html=True)

# פונקציית עזר ליצירת כרטיסיות
def render_metric(label, value, icon="💰", delta=None, is_currency=True):
    val_str = f"₪{value:,.0f}" if is_currency else f"{value:,}"
    delta_html = ""
    if delta is not None:
        color = "#10b981" if delta >= 0 else "#ef4444"
        sign = "+" if delta >= 0 else ""
        delta_html = f'<div style="color: {color}; font-size: 0.95rem; font-weight: 800; margin-top: 8px; background: {color}20; display: inline-block; padding: 4px 12px; border-radius: 20px;">{sign}₪{abs(delta):,.0f}</div>'

    return f"""
    <div class="metric-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div class="metric-label">{label}</div>
            <div style="font-size: 1.6rem; background: #e0e7ff; color: #4f46e5; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: 16px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">{icon}</div>
        </div>
        <div class="metric-value">{val_str}</div>
        {delta_html}
    </div>
    """

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
            st.error("הקובץ לא תואם למבנה המוכר של חברת האשראי.")
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
    st.markdown('<div class="main-title">💸 הפיננסים שלי</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">שליטה מלאה, תובנות חכמות וניהול צבעוני וחי מכל מקום</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📊 דשבורד נוכחי (גוגל שיטס)", "📥 ניתוח אקסל מהבנק"])
    
    with tab1:
        total_spent = float(df_tx["סכום"].sum()) if not df_tx.empty else 0.0
        income_planned = sum(BUDGET_PLAN.values())
        balance = income_planned - total_spent

        current_month = pd.Timestamp.today().month
        current_year = pd.Timestamp.today().year
        if not df_tx.empty and "תאריך_dt" in df_tx.columns:
            month_df = df_tx[(df_tx["תאריך_dt"].dt.month == current_month) & (df_tx["תאריך_dt"].dt.year == current_year)].copy()
        else:
            month_df = df_tx.copy()

        recent_df = month_df.sort_values("תאריך_dt", ascending=False).head(8).copy() if not month_df.empty else pd.DataFrame()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(render_metric("תקציב מתוכנן", income_planned, "🎯"), unsafe_allow_html=True)
        with c2:
            st.markdown(render_metric("סה״כ הוצאות", total_spent, "💸"), unsafe_allow_html=True)
        with c3:
            st.markdown(render_metric("יתרה נוכחית", balance, "⚖️", delta=balance), unsafe_allow_html=True)
        with c4:
            st.markdown(render_metric("עסקאות החודש", len(month_df), "🧾", is_currency=False), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        left, right = st.columns([1.1, 0.9])

        with left:
            st.markdown('<div class="section-box">', unsafe_allow_html=True)
            st.markdown("<h3 style='color: #1e293b; margin-bottom: 25px;'>🛒 הוספת הוצאה מהירה</h3>", unsafe_allow_html=True)
            with st.form("add_tx_form", clear_on_submit=True):
                col_form1, col_form2 = st.columns(2)
                with col_form1:
                    date = st.date_input("תאריך", datetime.today())
                    amount = st.number_input("סכום (₪)", min_value=0.0, step=10.0)
                with col_form2:
                    business = st.selectbox("שם בית העסק (מילון)", options=[""] + business_names, index=0)
                    category = st.selectbox("סיווג תקציבי", CATEGORIES)
                
                business_manual = st.text_input("הזנה ידנית - הקלד עסק חדש (אם לא מופיע למעלה)")
                note = st.text_input("הערות (אופציונלי)")
                
                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("➕ שלח נתונים לתקציב", type="primary")

                if submitted:
                    chosen_business = business_manual.strip() if business_manual.strip() else business.strip()
                    if chosen_business and amount > 0:
                        cat_val = category if category != "עסק מוכר - סווג אוטומטית לפי מילון" else ""
                        client = get_gspread_client()
                        wb = client.open_by_url(SPREADSHEET_URL)
                        tx_sheet = wb.worksheet("תנועות_אשראי")
                        tx_sheet.append_row([date.strftime('%d/%m/%Y'), chosen_business, float(amount), cat_val])
                        load_data.clear()
                        st.success(f"✅ ההוצאה עבור {chosen_business} נשמרה בהצלחה!")
                    else:
                        st.error("נא לבחור עסק ולהזין סכום תקין.")
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            st.markdown('<div class="section-box">', unsafe_allow_html=True)
            st.markdown("<h3 style='color: #1e293b; margin-bottom: 25px;'>📋 עסקאות אחרונות</h3>", unsafe_allow_html=True)
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
        st.markdown("<h3 style='color: #1e293b; margin-bottom: 10px;'>📥 מנוע סריקת קבצי אשראי</h3>", unsafe_allow_html=True)
        st.write("זרוק לכאן את קובץ ה-Excel של חברת האשראי, וקבל ניתוח צבעוני מול יעד התקציב שלך.")
        
        uploaded_file = st.file_uploader("", type=["xlsx"])
        
        if uploaded_file is not None:
            df_up = process_uploaded_excel(uploaded_file, df_dict)
            if df_up is not None and not df_up.empty:
                up_total = df_up["סכום"].sum()
                st.success(f"הקובץ נקלט בהצלחה! סך החיובים: ₪{up_total:,.0f}")
                
                st.markdown("<h3 style='margin-top: 30px; margin-bottom:20px; color:#1e293b;'>🎯 מדדי ניצול תקציב</h3>", unsafe_allow_html=True)
                
                html_bars = '<div style="margin-top: 20px;">'
                total_planned_budget = sum(BUDGET_PLAN.values())
                
                if total_planned_budget > 0:
                    overall_percent = (up_total / total_planned_budget) * 100
                else:
                    overall_percent = 100 if up_total > 0 else 0
                    
                overall_clamped = min(overall_percent, 100)
                
                # צבעי ברים עזים יותר
                if overall_percent <= 75:
                    overall_color = "#10b981" # ירוק בוהק
                elif overall_percent <= 100:
                    overall_color = "#f59e0b" # צהוב-כתום
                else:
                    overall_color = "#ef4444" # אדום חי
                
                overall_html = (
                    '<div style="margin-bottom: 40px; direction: rtl; padding: 24px; background: linear-gradient(135deg, #ffffff 0%, #f4f7fc 100%); border-radius: 20px; border: 2px solid #e2e8f0; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);">'
                    '<div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px;">'
                    '<div>'
                    '<div style="font-weight: 800; color: #1e293b; font-size: 1.5rem;">סה״כ הוצאות מול תקציב</div>'
                    '<div style="color: #64748b; font-size: 1rem; margin-top: 4px;">תמונת מצב מקיפה</div>'
                    '</div>'
                    '<div style="text-align: left;">'
                    '<span style="font-size: 2rem; font-weight: 800; color: #1e293b;">₪' + f"{up_total:,.0f}" + '</span> '
                    '<span style="color: #64748b; font-size: 1.2rem; margin-right: 8px;">מתוך ₪' + f"{total_planned_budget:,.0f}" + '</span>'
                    '<div style="color: ' + overall_color + '; font-weight: 800; font-size: 1.3rem; margin-top: -2px;">' + f"{overall_percent:.0f}" + '%</div>'
                    '</div>'
                    '</div>'
                    '<div style="background-color: #e2e8f0; border-radius: 16px; height: 28px; width: 100%; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">'
                    '<div style="background: linear-gradient(90deg, ' + overall_color + '99, ' + overall_color + '); height: 100%; width: ' + f"{overall_clamped}" + '%; border-radius: 16px; transition: width 1s ease; position: relative;">'
                    '<div class="shimmer-effect"></div>'
                    '</div>'
                    '</div>'
                    '</div>'
                )
                html_bars += overall_html
                
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
                        bar_color = "#34d399" # ירוק מואר
                    elif percent <= 100:
                        bar_color = "#fbbf24" # צהוב מואר
                    else:
                        bar_color = "#f87171" # אדום מואר
                        
                    bar_html = (
                        '<div style="margin-bottom: 24px; direction: rtl;">'
                        '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">'
                        '<span style="font-weight: 700; color: #1e293b; font-size: 1.1rem;">' + cat + '</span>'
                        '<span style="color: #475569; font-size: 1rem;">'
                        '<strong style="color:#0f172a;">₪' + f"{spent:,.0f}" + '</strong> מתוך ₪' + f"{limit:,.0f}" + ' '
                        '<span style="background: ' + bar_color + '20; color: ' + bar_color + '; font-weight: 800; padding: 4px 10px; border-radius: 12px; margin-right: 8px;">' + f"{percent:.0f}" + '%</span>'
                        '</span>'
                        '</div>'
                        '<div style="background-color: #f1f5f9; border-radius: 12px; height: 18px; width: 100%; overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);">'
                        '<div style="background: linear-gradient(90deg, ' + bar_color + 'aa, ' + bar_color + '); height: 100%; width: ' + f"{clamped_percent}" + '%; border-radius: 12px; transition: width 0.8s ease;"></div>'
                        '</div>'
                        '</div>'
                    )
                    html_bars += bar_html
                
                unassigned_spent = df_up[df_up["קטגוריה_לתצוגה"] == "לא משויך"]["סכום"].sum()
                if unassigned_spent > 0:
                    unassigned_html = (
                        '<div style="margin-bottom: 24px; direction: rtl;">'
                        '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">'
                        '<span style="font-weight: 700; color: #1e293b; font-size: 1.1rem;">לא משויך (ללא תקציב)</span>'
                        '<span style="color: #ef4444; font-size: 1rem;">'
                        'סה"כ נוצל: <strong style="color:#ef4444;">₪' + f"{unassigned_spent:,.0f}" + '</strong>'
                        '</span>'
                        '</div>'
                        '<div style="background-color: #f1f5f9; border-radius: 12px; height: 18px; width: 100%; overflow: hidden;">'
                        '<div style="background-color: #94a3b8; height: 100%; width: 100%; border-radius: 12px;"></div>'
                        '</div>'
                        '</div>'
                    )
                    html_bars += unassigned_html
                    
                html_bars += '</div>'
                st.markdown(html_bars, unsafe_allow_html=True)
                
                st.markdown("<hr style='margin: 40px 0; border: 0; border-top: 2px solid #e2e8f0;'>", unsafe_allow_html=True)
                
                # סידור העמודות: למעלה הגרף, למטה הטבלה (כדי שהגרף לא יחתך במובייל)
                st.markdown("<h3 style='color: #1e293b; text-align:center; margin-bottom:20px;'>🍩 התפלגות קטגוריות</h3>", unsafe_allow_html=True)
                
                up_cat = df_up.groupby("קטגוריה_לתצוגה")["סכום"].sum().reset_index().sort_values("סכום", ascending=False)
                
                # גרף צבעוני ועשיר שמותאם למסכים קטנים
                fig_up = px.pie(up_cat, names="קטגוריה_לתצוגה", values="סכום", hole=0.45,
                                color_discrete_sequence=px.colors.qualitative.Prism) # פלטת צבעים עשירה וברורה
                
                # עיצוב מותאם מובייל (המקרא מתחת לגרף ולא נחתך)
                fig_up.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=500,
                    font=dict(family="Heebo", size=14),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.1,
                        xanchor="center",
                        x=0.5
                    )
                )
                fig_up.update_traces(textposition='inside', textinfo='percent+label')
                
                st.plotly_chart(fig_up, use_container_width=True)
                
                st.markdown("<h3 style='color: #1e293b; margin-top:30px; margin-bottom:15px;'>🧾 פירוט העסקאות</h3>", unsafe_allow_html=True)
                show_up = df_up[["תאריך", "שם עסק באשראי", "קטגוריה_לתצוגה", "סכום"]].copy()
                show_up["סכום"] = show_up["סכום"].map(lambda x: f"₪{x:,.0f}")
                st.dataframe(show_up, use_container_width=True, hide_index=True)
                    
            elif df_up is not None and df_up.empty:
                st.warning("הקובץ נקרא בהצלחה, אך לא נמצאו בו שורות תקינות עם תאריך וסכום.")
                
        st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error("שגיאת התחברות למסד הנתונים או ריצה. בדוק את הלוגים.")
    st.write(e)
