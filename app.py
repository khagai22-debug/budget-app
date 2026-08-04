import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import plotly.express as px
import pdfplumber
import tempfile
import os

# הגדרות עמוד (חייב להיות ראשון)
st.set_page_config(page_title="מערכת תקציב אישי - AI Advisor", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

CATEGORIES = [
    "עסק מוכר - סווג אוטומטית לפי מילון",
    "הכנסות - משכורת וקצבאות",
    "הכנסות - החזרי מס ושונות",
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
    "מזון וסופר": 4000,
    "אחזקת רכב (דלק, שטיפה, חניה)": 800,
    "חשבונות": 1000,
    "בריאות ופארם": 700,
    "ביטוחים": 1600,
    "חינוך ומסגרות": 3100,
    "פנאי, מסעדות וקניות": 1800,
    "תרומות וקהילה": 400,
    "אפליקציות תשלום (דורש בירור)": 500,
}

# עיצוב פרימיום
CSS_CODE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;800&display=swap');

.stApp { background-color: #f4f7fc; }
html, body, [class*="css"] { font-family: 'Heebo', sans-serif !important; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px; direction: rtl; text-align: right; }

.hero-box {
    background: linear-gradient(135deg, #1e1b4b 0%, #4338ca 100%);
    color: white; border-radius: 24px; padding: 40px 30px;
    box-shadow: 0 20px 25px -5px rgba(67, 56, 202, 0.4);
    margin-bottom: 2.5rem; text-align: center; position: relative; overflow: hidden;
}
.hero-box::before {
    content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%); pointer-events: none;
}
.main-title { font-size: 3rem; font-weight: 800; margin-bottom: 0.5rem; color: #ffffff; text-shadow: 0 4px 10px rgba(0,0,0,0.3); }
.subtitle { color: #e0e7ff; font-size: 1.2rem; font-weight: 400; }

.metric-card {
    background: white; border-bottom: 4px solid #4f46e5; border-radius: 20px; padding: 24px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05); transition: transform 0.3s ease, box-shadow 0.3s ease; margin-bottom: 1rem;
}
.metric-card:hover { transform: translateY(-5px); box-shadow: 0 20px 25px -5px rgba(79, 70, 229, 0.15); border-bottom: 4px solid #8b5cf6; }
.metric-label { color: #475569; font-size: 1.1rem; font-weight: 600; }
.metric-value { font-size: 2.2rem; font-weight: 800; color: #1e293b; margin-top: 4px; }

.section-box { background: white; border: 1px solid #e2e8f0; border-radius: 24px; padding: 30px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05); height: 100%; margin-bottom: 20px;}

.stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #e2e8f0; border-radius: 16px; padding: 8px; margin-bottom: 24px; }
.stTabs [data-baseweb="tab"] { border-radius: 12px; padding: 12px 24px; color: #475569; font-weight: 600; transition: all 0.2s; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important; color: white !important; box-shadow: 0 4px 10px rgba(79, 70, 229, 0.3); }

.stButton > button { border-radius: 12px !important; font-weight: 600 !important; padding: 10px 24px !important; transition: all 0.3s ease !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important; color: white !important; border: none !important; box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3) !important; }
.stButton > button[kind="primary"]:hover { box-shadow: 0 8px 15px rgba(59, 130, 246, 0.5) !important; transform: translateY(-2px) !important; }

.advisor-box { background: linear-gradient(to left, #f8fafc, #ffffff); border-right: 5px solid #10b981; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
.advisor-title { font-size: 1.3rem; font-weight: 800; color: #0f172a; margin-bottom: 10px; display: flex; align-items: center; gap: 10px;}
.advisor-text { font-size: 1.1rem; color: #334155; line-height: 1.6;}
.savings-box { background: #fffbeb; border: 1px solid #fde68a; border-radius: 16px; padding: 15px 20px; margin-bottom: 15px; display: flex; align-items: center; justify-content: space-between; }
.savings-amount { font-size: 1.5rem; font-weight: 800; color: #d97706; }
.smart-assign-box { background: linear-gradient(to right, #fffbeb, #e0e7ff); border: 2px solid #8b5cf6; border-radius: 20px; padding: 24px; margin-top: 40px; }
</style>
"""
st.markdown(CSS_CODE, unsafe_allow_html=True)

def render_metric(label, value, icon="💰", delta=None, is_currency=True, invert_colors=False):
    val_str = f"₪{value:,.0f}" if is_currency else f"{value:,}"
    delta_html = ""
    if delta is not None:
        color = "#ef4444" if (delta >= 0 and invert_colors) or (delta < 0 and not invert_colors) else "#10b981"
        sign = "+" if delta > 0 else ""
        delta_html = f'<div style="color: {color}; font-size: 0.95rem; font-weight: 800; margin-top: 8px; background: {color}20; display: inline-block; padding: 4px 12px; border-radius: 20px;">{sign}₪{delta:,.0f}</div>'

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
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
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
        business_names = sorted([str(x).strip() for x in df_dict[df_dict.columns[0]].dropna().tolist() if str(x).strip()]) if not df_dict.empty else []
    except:
        business_names = []
        df_dict = pd.DataFrame()

    tx_rows = tx_sheet.get_all_records()
    df_tx = pd.DataFrame(tx_rows)

    if not df_tx.empty:
        df_tx = df_tx.rename(columns=lambda x: str(x).strip())
        df_tx["סכום"] = pd.to_numeric(df_tx.get("סכום", 0), errors="coerce").fillna(0)
        df_tx["תאריך_dt"] = pd.to_datetime(df_tx.get("תאריך"), dayfirst=True, errors="coerce")
        cat_col = next((c for c in df_tx.columns if "שיוך" in c or "קטגור" in c), None)
        df_tx["קטגוריה_לתצוגה"] = df_tx[cat_col].replace("", pd.NA).fillna("לא משויך") if cat_col else "לא משויך"
    else:
        df_tx = pd.DataFrame(columns=["תאריך", "שם עסק באשראי", "סכום", "קטגוריה_לתצוגה", "תאריך_dt"])

    return df_tx, business_names, df_dict

def apply_dictionary(biz_name, df_dict):
    biz_str = str(biz_name).strip()
    if df_dict.empty or len(df_dict.columns) < 2: return "לא משויך"
    biz_col, cat_col = df_dict.columns[0], df_dict.columns[1]
    dict_mapping = dict(zip(df_dict[biz_col].astype(str).str.strip(), df_dict[cat_col].astype(str).str.strip()))
    if biz_str in dict_mapping: return dict_mapping[biz_str]
    for k, v in dict_mapping.items():
        if k and k in biz_str: return v
    return "לא משויך"

def process_uploaded_excel(uploaded_file, df_dict):
    try:
        df_uploaded = pd.read_excel(uploaded_file, header=3)
        df_uploaded.columns = [str(c).strip() for c in df_uploaded.columns]
        if "תאריך עסקה" not in df_uploaded.columns or "סכום חיוב" not in df_uploaded.columns: return None
        df_mapped = pd.DataFrame()
        df_mapped["תאריך"] = df_uploaded["תאריך עסקה"]
        df_mapped["תאריך_dt"] = pd.to_datetime(df_uploaded["תאריך עסקה"], format='%d-%m-%Y', errors="coerce")
        df_mapped["שם עסק באשראי"] = df_uploaded["שם בית העסק"].astype(str).str.strip()
        df_mapped["סכום"] = pd.to_numeric(df_uploaded["סכום חיוב"], errors="coerce").fillna(0)
        df_mapped = df_mapped.dropna(subset=["תאריך_dt"])
        df_mapped["קטגוריה_לתצוגה"] = df_mapped["שם עסק באשראי"].apply(lambda x: apply_dictionary(x, df_dict))
        return df_mapped
    except: return None

import re
def process_mizrahi_pdf(pdf_file, df_dict):
    try:
        import pdfplumber
        rows = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                for line in text.split():
                    match = re.search(r'(d{2}/d{2}/d{4})', line)
                    if match:
                        date_str = match.group(1)
                        rest = line[match.end():].strip()
                        amount_matches = list(re.finditer(r'((?:d{1,3},)?d{1,3}.d{2}-?)', rest))
                        if amount_matches:
                            amount_str = amount_matches[0].group(1)
                            desc = rest[:amount_matches[0].start()].strip()
                            desc = desc[::-1].replace(')(', '()').strip()
                            desc = re.sub(r'^(w)', '', desc).strip()
                            is_negative = '-' in amount_str
                            amount_val = float(amount_str.replace(',', '').replace('-', ''))
                            if is_negative: amount_val = -amount_val
                            if amount_val != 0:
                                rows.append({
                                    'תאריך': date_str,
                                    'תאריך_dt': pd.to_datetime(date_str, format='%d/%m/%Y'),
                                    'שם פעולה': desc,
                                    'סכום': amount_val,
                                    'סוג': 'הוצאה' if amount_val < 0 else 'הכנסה',
                                    'סכום_אבסולוטי': abs(amount_val)
                                })
        if not rows: return None
        df_mapped = pd.DataFrame(rows)
        df_mapped["קטגוריה_לתצוגה"] = df_mapped["שם פעולה"].apply(lambda x: apply_dictionary(x, df_dict))
        return df_mapped
    except Exception as e:
        st.error(f"שגיאה בקריאת ה-PDF: {e}")
        return None

def process_bank_excel(uploaded_file, df_dict):
    try:
        df_raw = pd.read_excel(uploaded_file)
        header_row = -1
        for i in range(min(15, len(df_raw))):
            row_vals = df_raw.iloc[i].astype(str).tolist()
            if any("תאריך" in val for val in row_vals) and any("זכות" in val or "חובה" in val or "סכום" in val for val in row_vals):
                header_row = i; break
        df_bank = pd.read_excel(uploaded_file, header=header_row + 1) if header_row >= 0 else df_raw
        df_bank.columns = [str(c).strip() for c in df_bank.columns]
        
        date_col = next((c for c in df_bank.columns if "תאריך" in c), None)
        desc_col = next((c for c in df_bank.columns if "תיאור" in c or "פרטים" in c), None)
        hova_col = next((c for c in df_bank.columns if "חובה" in c), None)
        zchut_col = next((c for c in df_bank.columns if "זכות" in c), None)
        amount_col = next((c for c in df_bank.columns if "סכום" in c and c not in [hova_col, zchut_col]), None)

        if not date_col or not desc_col: return None
        df_mapped = pd.DataFrame()
        df_mapped["תאריך"] = df_bank[date_col]
        df_mapped["תאריך_dt"] = pd.to_datetime(df_bank[date_col], dayfirst=True, errors="coerce")
        df_mapped["שם פעולה"] = df_bank[desc_col].astype(str).str.strip()
        
        if hova_col and zchut_col:
            hova = pd.to_numeric(df_bank[hova_col], errors="coerce").fillna(0)
            zchut = pd.to_numeric(df_bank[zchut_col], errors="coerce").fillna(0)
            df_mapped["סכום"] = zchut - hova
        elif amount_col:
            df_mapped["סכום"] = pd.to_numeric(df_bank[amount_col], errors="coerce").fillna(0)
        else: return None
        
        df_mapped["סוג"] = df_mapped["סכום"].apply(lambda x: "הכנסה" if x > 0 else "הוצאה")
        df_mapped["סכום_אבסולוטי"] = df_mapped["סכום"].abs()
        df_mapped = df_mapped.dropna(subset=["תאריך_dt"])
        df_mapped = df_mapped[df_mapped["סכום"] != 0]
        df_mapped["קטגוריה_לתצוגה"] = df_mapped["שם פעולה"].apply(lambda x: apply_dictionary(x, df_dict))
        return df_mapped
    except: return None

SPREADSHEET_URL = st.secrets.get("spreadsheet_url", "")

try:
    df_tx, business_names, df_dict = load_data(SPREADSHEET_URL)
    
    st.markdown('<div class="hero-box">', unsafe_allow_html=True)
    st.markdown('<div class="main-title">💸 הפיננסים שלי & AI Advisor</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">השוואות לממוצע, המלצות ייעול, תנועות עו"ש וניהול נתונים חכם</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🤖 יועץ פיננסי אוטומטי (AI)",
        "📊 דשבורד חודשי", 
        "💳 ניתוח קובץ אשראי", 
        "🏦 תנועות עובר ושב (PDF/Excel)",
        "⚙️ ניהול מילון"
    ])
    
    # -------------------------------------------------------------
    # TAB 1: AI Advisor & Annual Comparison
    # -------------------------------------------------------------
    with tab1:
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown("<h3 style='color: #1e293b; margin-bottom: 20px;'>🤖 מסקנות והמלצות יועץ פיננסי</h3>", unsafe_allow_html=True)
        
        current_month = pd.Timestamp.today().month
        current_year = pd.Timestamp.today().year
        
        if not df_tx.empty and "תאריך_dt" in df_tx.columns:
            df_tx['Month_Year'] = df_tx['תאריך_dt'].dt.to_period('M')
            monthly_totals = df_tx.groupby('Month_Year')['סכום'].sum()
            annual_avg = monthly_totals.mean() if len(monthly_totals) > 0 else 0
            current_month_df = df_tx[(df_tx["תאריך_dt"].dt.month == current_month) & (df_tx["תאריך_dt"].dt.year == current_year)]
            current_spent = current_month_df['סכום'].sum()
            
            # נתונים מציאותיים מהניתוח שביצענו
            true_monthly_income = 29510
            true_monthly_expenses = 31197
            
            st.markdown("#### 📉 החודש הנוכחי לעומת הממוצע השנתי (אשראי מאגר)")
            c_comp1, c_comp2, c_comp3 = st.columns(3)
            with c_comp1:
                st.markdown(render_metric("הוצאות החודש", current_spent, "📅"), unsafe_allow_html=True)
            with c_comp2:
                st.markdown(render_metric("ממוצע חודשי (שנתי)", annual_avg, "📈"), unsafe_allow_html=True)
            with c_comp3:
                diff = current_spent - annual_avg
                status_icon = "🔥" if diff > 0 else "✅"
                st.markdown(render_metric("הפרש מהממוצע", diff, status_icon, delta=diff, invert_colors=True), unsafe_allow_html=True)

            st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)

            st.markdown(f"""
            <div class="advisor-box">
                <div class="advisor-title">💡 הניתוח הפיננסי שלך (עו"ש + אשראי)</div>
                <div class="advisor-text">
                    <strong>תמונת מצב מקיפה:</strong> ההכנסה הממוצעת שלך עומדת על כ-₪{true_monthly_income:,.0f}, אך ההוצאה הממוצעת הכוללת היא כ-₪{true_monthly_expenses:,.0f}.
                    <br>השודד השקט שלך הוא לא ההוצאות הקבועות הרגילות, אלא פיזור נרחב בכרטיסי האשראי והעברות דרך אפליקציות תשלום.<br>
                    כדי להעביר את התזרים למצב חיובי יציב, יש לחסוך כ-1,700 ₪ עד 3,000 ₪ בחודש.
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("#### ✂️ איפה אפשר לחסוך בפועל כל חודש?")
            
            potential_savings = [
    {
        "title": "אפליקציות תשלום - Bit ו-Paybox",
        "amount": 2800,
        "desc": "ראינו העברות קבועות וגדולות שלא מסווגות היטב, כולל תשלומים חוזרים של כ-2100 שקלים. חשוב לברר ולשייך כל העברה מראש."
    },
    {
        "title": "חנויות נוחות והשלמות - Yellow ו-Cello",
        "amount": 300,
        "desc": "יש רכישות חוזרות בתחנות ובחנויות נוחות. העברת קניות ההשלמה לסופר עשויה לחסוך חלק גדול מהסכום."
    },
    {
        "title": "ביטוחים",
        "amount": 500,
        "desc": "זוהו קפיצות בחיובי ביטוח. כדאי לבדוק כפל פוליסות ותמחור דרך אתר הר הביטוח."
    },
    {
        "title": "ביגוד וילדים",
        "amount": 200,
        "desc": "זוהו רכישות במספר חנויות ביגוד. קנייה מרוכזת לפי עונה יכולה להפחית קניות דחף."
    }
                           ]
            
            for item in potential_savings:
                st.markdown(f"""
                <div class="savings-box">
                    <div>
                        <div style="font-weight: 800; font-size: 1.2rem; color: #1e293b;">{item['title']}</div>
                        <div style="color: #475569; margin-top: 4px;">{item['desc']}</div>
                    </div>
                    <div class="savings-amount">~₪{item['amount']:,.0f} חיסכון</div>
                </div>
                """, unsafe_allow_html=True)
                
            total_pot = sum(x['amount'] for x in potential_savings)
            st.success(f"**סך פוטנציאל חיסכון חודשי: ₪{total_pot:,.0f}** - זה הסכום שיכול להפוך את המינוס לפלוס!")
            
            st.markdown("#### 📊 מגמת ההוצאות שלך לאורך השנה האחרונה")
            monthly_totals.index = monthly_totals.index.astype(str)
            fig_trend = px.bar(x=monthly_totals.index, y=monthly_totals.values, labels={'x':'חודש', 'y':'הוצאות (₪)'})
            fig_trend.add_hline(y=annual_avg, line_dash="dash", line_color="red", annotation_text="ממוצע שנתי")
            fig_trend.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=350, font=dict(family="Heebo", size=14))
            fig_trend.update_traces(marker_color='#4f46e5', marker_line_color='#1e1b4b', marker_line_width=1.5, opacity=0.8)
            st.plotly_chart(fig_trend, use_container_width=True)

        else:
            st.info("עדיין אין מספיק נתונים במאגר כדי לייצר השוואה והמלצות יועץ. התחל להזין הוצאות!")
            
        st.markdown('</div>', unsafe_allow_html=True)
    
    # -------------------------------------------------------------
    # TAB 2: דשבורד חודשי
    # -------------------------------------------------------------
    with tab2:
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
        with c1: st.markdown(render_metric("תקציב מתוכנן", income_planned, "🎯"), unsafe_allow_html=True)
        with c2: st.markdown(render_metric("סה״כ הוצאות (מאגר)", total_spent, "💸"), unsafe_allow_html=True)
        with c3: st.markdown(render_metric("יתרה נוכחית", balance, "⚖️", delta=balance), unsafe_allow_html=True)
        with c4: st.markdown(render_metric("עסקאות החודש", len(month_df), "🧾", is_currency=False), unsafe_allow_html=True)

        left, right = st.columns([1.1, 0.9])
        with left:
            st.markdown('<div class="section-box">', unsafe_allow_html=True)
            st.markdown("<h3 style='color: #1e293b; margin-bottom: 25px;'>🛒 הוספת הוצאה מהירה למאגר</h3>", unsafe_allow_html=True)
            with st.form("add_tx_form", clear_on_submit=True):
                col_form1, col_form2 = st.columns(2)
                with col_form1:
                    date = st.date_input("תאריך", datetime.today())
                    amount = st.number_input("סכום (₪)", min_value=0.0, step=10.0)
                with col_form2:
                    business = st.selectbox("שם בית העסק (מילון)", options=[""] + business_names, index=0)
                    category = st.selectbox("סיווג תקציבי", CATEGORIES)
                
                business_manual = st.text_input("הזנה ידנית - הקלד עסק חדש")
                submitted = st.form_submit_button("➕ שלח נתונים למאגר", type="primary", use_container_width=True)

                if submitted:
                    chosen_business = business_manual.strip() if business_manual.strip() else business.strip()
                    if chosen_business and amount > 0:
                        cat_val = category if category != "עסק מוכר - סווג אוטומטית לפי מילון" else ""
                        get_gspread_client().open_by_url(SPREADSHEET_URL).worksheet("תנועות_אשראי").append_row([date.strftime('%d/%m/%Y'), chosen_business, float(amount), cat_val])
                        load_data.clear()
                        st.success(f"✅ ההוצאה עבור {chosen_business} נשמרה בהצלחה!")
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            st.markdown('<div class="section-box">', unsafe_allow_html=True)
            st.markdown("<h3 style='color: #1e293b; margin-bottom: 25px;'>📋 עסקאות אחרונות במאגר</h3>", unsafe_allow_html=True)
            if recent_df.empty: st.info("עדיין אין עסקאות להצגה.")
            else:
                display_cols = [c for c in ["תאריך", "שם עסק באשראי", "סכום", "קטגוריה_לתצוגה"] if c in recent_df.columns]
                show_df = recent_df[display_cols].copy()
                show_df["סכום"] = show_df["סכום"].map(lambda x: f"₪{x:,.0f}")
                st.dataframe(show_df, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 3: ניתוח קובץ אשראי
    # -------------------------------------------------------------
    with tab3:
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown("<h3 style='color: #1e293b; margin-bottom: 10px;'>💳 ניתוח קובץ כרטיס אשראי</h3>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("העלה פירוט אשראי (Excel)", type=["xlsx"], key="cc_up")
        
        if uploaded_file is not None:
            df_up = process_uploaded_excel(uploaded_file, df_dict)
            if df_up is not None and not df_up.empty:
                up_total = df_up["סכום"].sum()
                st.success(f"הקובץ נקלט בהצלחה! סך החיובים באשראי: ₪{up_total:,.0f}")
                
                df_up['row_id'] = range(len(df_up))
                pay_mask = (df_up["קטגוריה_לתצוגה"] == "אפליקציות תשלום (דורש בירור)") | \
                           ((df_up["קטגוריה_לתצוגה"] == "לא משויך") & df_up["שם עסק באשראי"].astype(str).str.upper().str.contains("BIT|PAYBOX|APPLE PAY|GOOGLE PAY", regex=True, na=False))
                
                if pay_mask.any():
                    st.markdown('<div class="smart-assign-box" style="margin-top: 10px; margin-bottom: 30px; border-color: #3b82f6; background: linear-gradient(to right, #eff6ff, #ffffff);">', unsafe_allow_html=True)
                    st.markdown("<h3 style='color: #3b82f6; margin-bottom: 5px;'>📱 בירור עסקאות באפליקציות תשלום</h3>", unsafe_allow_html=True)
                    df_pay = df_up[pay_mask][['row_id', 'תאריך', 'שם עסק באשראי', 'סכום', 'קטגוריה_לתצוגה']].copy()
                    df_pay['תאריך'] = df_pay['תאריך'].astype(str).str.split(' ').str[0]
                    valid_cats = [c for c in CATEGORIES if c not in ["עסק מוכר - סווג אוטומטית לפי מילון"]]
                    
                    edited_pay = st.data_editor(
                        df_pay,
                        column_config={
                            "row_id": None, "תאריך": st.column_config.TextColumn("תאריך", disabled=True),
                            "שם עסק באשראי": st.column_config.TextColumn("שם עסק", disabled=True),
                            "סכום": st.column_config.NumberColumn("סכום", format="₪%.0f", disabled=True),
                            "קטגוריה_לתצוגה": st.column_config.SelectboxColumn("קטגוריה", options=valid_cats, required=True)
                        }, hide_index=True, use_container_width=True, key="pay_apps_editor"
                    )
                    for _, row in edited_pay.iterrows():
                        df_up.loc[df_up['row_id'] == row['row_id'], 'קטגוריה_לתצוגה'] = row['קטגוריה_לתצוגה']
                    st.markdown('</div>', unsafe_allow_html=True)
                
                html_bars = f"<h3 style='margin-top: 30px; margin-bottom:20px; color:#1e293b;'>🎯 מדדי ניצול תקציב (אשראי)</h3><div style='margin-top: 20px;'>"
                total_planned_budget = sum(BUDGET_PLAN.values())
                overall_percent = (up_total / total_planned_budget) * 100 if total_planned_budget > 0 else 100
                overall_clamped = min(overall_percent, 100)
                overall_color = "#10b981" if overall_percent <= 75 else "#f59e0b" if overall_percent <= 100 else "#ef4444"
                
                html_bars += f"""
                    <div style="margin-bottom: 40px; direction: rtl; padding: 24px; background: linear-gradient(135deg, #ffffff 0%, #f4f7fc 100%); border-radius: 20px; border: 2px solid #e2e8f0; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px;">
                    <div><div style="font-weight: 800; color: #1e293b; font-size: 1.5rem;">סה״כ אשראי מול תקציב</div></div>
                    <div style="text-align: left;"><span style="font-size: 2rem; font-weight: 800; color: #1e293b;">₪{up_total:,.0f}</span> 
                    <span style="color: #64748b; font-size: 1.2rem; margin-right: 8px;">מתוך ₪{total_planned_budget:,.0f}</span>
                    <div style="color: {overall_color}; font-weight: 800; font-size: 1.3rem; margin-top: -2px;">{overall_percent:.0f}%</div>
                    </div></div><div style="background-color: #e2e8f0; border-radius: 16px; height: 28px; width: 100%; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, {overall_color}99, {overall_color}); height: 100%; width: {overall_clamped}%; border-radius: 16px; position: relative;"><div class="shimmer-effect"></div></div>
                    </div></div>
                """
                
                for cat in CATEGORIES:
                    if cat in ["עסק מוכר - סווג אוטומטית לפי מילון", "משיכה מקופת רכב (לא נכנס לתקציב שוטף)", "לא משויך", "הכנסות - משכורת וקצבאות", "הכנסות - החזרי מס ושונות"]: continue
                    limit = BUDGET_PLAN.get(cat, 0)
                    spent = df_up[df_up["קטגוריה_לתצוגה"] == cat]["סכום"].sum()
                    if limit == 0: continue
                    percent = (spent / limit) * 100
                    clamped_percent = min(percent, 100)
                    bar_color = "#34d399" if percent <= 75 else "#fbbf24" if percent <= 100 else "#f87171"
                    html_bars += f"""
                        <div style="margin-bottom: 24px; direction: rtl;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <span style="font-weight: 700; color: #1e293b; font-size: 1.1rem;">{cat}</span>
                        <span style="color: #475569; font-size: 1rem;"><strong style="color:#0f172a;">₪{spent:,.0f}</strong> מתוך ₪{limit:,.0f} 
                        <span style="background: {bar_color}20; color: {bar_color}; font-weight: 800; padding: 4px 10px; border-radius: 12px; margin-right: 8px;">{percent:.0f}%</span></span>
                        </div><div style="background-color: #f1f5f9; border-radius: 12px; height: 18px; width: 100%; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, {bar_color}aa, {bar_color}); height: 100%; width: {clamped_percent}%; border-radius: 12px;"></div>
                        </div></div>
                    """
                
                unassigned_spent = df_up[df_up["קטגוריה_לתצוגה"] == "לא משויך"]["סכום"].sum()
                if unassigned_spent > 0:
                    html_bars += f'<div style="margin-bottom: 24px; direction: rtl;"><div style="display: flex; justify-content: space-between; margin-bottom: 10px;"><span style="font-weight: 700; font-size: 1.1rem;">לא משויך</span><strong style="color:#ef4444;">₪{unassigned_spent:,.0f}</strong></div><div style="background-color: #f1f5f9; border-radius: 12px; height: 18px; width: 100%;"><div style="background-color: #94a3b8; height: 100%; width: 100%; border-radius: 12px;"></div></div></div>'
                
                st.markdown(html_bars + '</div>', unsafe_allow_html=True)
                st.markdown("<hr style='margin: 40px 0; border: 0; border-top: 2px solid #e2e8f0;'>", unsafe_allow_html=True)
                
                c_pie, c_table = st.columns(2)
                with c_pie:
                    st.markdown("<h4 style='color: #1e293b; text-align:center;'>🍩 התפלגות קטגוריות</h4>", unsafe_allow_html=True)
                    fig_up = px.pie(df_up.groupby("קטגוריה_לתצוגה")["סכום"].sum().reset_index(), names="קטגוריה_לתצוגה", values="סכום", hole=0.45, color_discrete_sequence=px.colors.qualitative.Prism)
                    fig_up.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400, legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5))
                    st.plotly_chart(fig_up, use_container_width=True)
                with c_table:
                    st.markdown("<h4 style='color: #1e293b; text-align:center;'>🧾 עסקאות אשראי</h4>", unsafe_allow_html=True)
                    show_up = df_up[["תאריך", "שם עסק באשראי", "קטגוריה_לתצוגה", "סכום"]].copy()
                    show_up["סכום"] = show_up["סכום"].map(lambda x: f"₪{x:,.0f}")
                    st.dataframe(show_up, use_container_width=True, hide_index=True, height=400)

                unassigned_in_file = df_up[df_up["קטגוריה_לתצוגה"] == "לא משויך"]
                if not unassigned_in_file.empty:
                    st.markdown('<div class="smart-assign-box">', unsafe_allow_html=True)
                    st.markdown("<h3 style='color: #4f46e5; margin-bottom: 5px;'>✨ מצאנו עסקים חדשים בקובץ!</h3>", unsafe_allow_html=True)
                    unassigned_list_file = [str(x).strip() for x in unassigned_in_file["שם עסק באשראי"].dropna().unique() if str(x).strip()]
                    
                    c1, c2 = st.columns(2)
                    with c1: selected_new_biz = st.selectbox("בחר עסק לא משויך:", unassigned_list_file, key="select_biz_cc")
                    with c2: selected_new_cat = st.selectbox("שייך לקטגוריה:", [c for c in CATEGORIES if c not in ["עסק מוכר - סווג אוטומטית לפי מילון", "לא משויך"]], key="select_cat_cc")
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 שמור למילון ורענן", type="primary", use_container_width=True):
                        try:
                            get_gspread_client().open_by_url(SPREADSHEET_URL).worksheet("מילון_עסקים").append_row([selected_new_biz, selected_new_cat])
                            load_data.clear()
                            st.success("שויך בהצלחה! העלה את הקובץ מחדש כדי לראות את העדכון.")
                        except Exception as e:
                            st.error(f"שגיאה: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
        st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 4: תנועות בנק (כולל קריאת PDF של מזרחי טפחות)
    # -------------------------------------------------------------
    with tab4:
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown("<h3 style='color: #1e293b; margin-bottom: 10px;'>🏦 ניתוח תנועות בנק (עובר ושב)</h3>", unsafe_allow_html=True)
        st.write("העלה את דפי החשבון מהבנק. המערכת תומכת בקבצי Excel, וכן בקבצי PDF של **בנק מזרחי טפחות**.")
        
        bank_file = st.file_uploader("העלה קובץ בנק (PDF או Excel)", type=["xlsx", "xls", "pdf"], key="bank_up")
        
        if bank_file is not None:
            df_bank = None
            if bank_file.name.lower().endswith('.pdf'):
                st.info("מזהה קובץ PDF... סורק שורות עבור בנק מזרחי טפחות...")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(bank_file.getvalue())
                    tmp_path = tmp.name
                df_bank = process_mizrahi_pdf(tmp_path, df_dict)
                os.unlink(tmp_path)
            else:
                df_bank = process_bank_excel(bank_file, df_dict)
            
            if df_bank is not None and not df_bank.empty:
                total_in = df_bank[df_bank["סוג"] == "הכנסה"]["סכום_אבסולוטי"].sum()
                total_out = df_bank[df_bank["סוג"] == "הוצאה"]["סכום_אבסולוטי"].sum()
                net_flow = total_in - total_out
                
                st.markdown("<h3 style='margin-top: 20px; color:#1e293b;'>⚖️ תזרים מזומנים בחשבון</h3>", unsafe_allow_html=True)
                
                c_in, c_out, c_net = st.columns(3)
                with c_in: st.markdown(render_metric("סה״כ הכנסות (זכות)", total_in, "🟢"), unsafe_allow_html=True)
                with c_out: st.markdown(render_metric("סה״כ הוצאות (חובה)", total_out, "🔴", invert_colors=True), unsafe_allow_html=True)
                with c_net: st.markdown(render_metric("תזרים נטו", net_flow, "🏦", delta=net_flow, invert_colors=True), unsafe_allow_html=True)
                    
                st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)
                
                c_table, c_pie = st.columns([1.2, 0.8])
                with c_table:
                    st.markdown("<h4 style='color: #1e293b;'>📋 פירוט תנועות בנק</h4>", unsafe_allow_html=True)
                    show_bank = df_bank[["תאריך", "שם פעולה", "סוג", "סכום_אבסולוטי", "קטגוריה_לתצוגה"]].copy()
                    def color_amount(row):
                        val = f"₪{row['סכום_אבסולוטי']:,.0f}"
                        return f"🟢 {val}" if row['סוג'] == 'הכנסה' else f"🔴 {val}"
                    show_bank["סכום"] = show_bank.apply(color_amount, axis=1)
                    show_bank = show_bank.drop(columns=["סכום_אבסולוטי", "סוג"])
                    st.dataframe(show_bank, use_container_width=True, hide_index=True, height=450)
                    
                with c_pie:
                    st.markdown("<h4 style='color: #1e293b;'>💸 לאן הלך הכסף? (הוצאות בבנק)</h4>", unsafe_allow_html=True)
                    df_out_only = df_bank[df_bank["סוג"] == "הוצאה"]
                    if not df_out_only.empty:
                        out_cat = df_out_only.groupby("קטגוריה_לתצוגה")["סכום_אבסולוטי"].sum().reset_index()
                        fig_b = px.pie(out_cat, names="קטגוריה_לתצוגה", values="סכום_אבסולוטי", hole=0.5, color_discrete_sequence=px.colors.sequential.RdBu)
                        fig_b.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=400, legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5))
                        st.plotly_chart(fig_b, use_container_width=True)
                        
                unassigned_bank = df_bank[(df_bank["קטגוריה_לתצוגה"] == "לא משויך")]
                if not unassigned_bank.empty:
                    st.markdown('<div class="smart-assign-box">', unsafe_allow_html=True)
                    st.markdown("<h3 style='color: #4f46e5; margin-bottom: 5px;'>✨ חסר סיווג לחלק מפעולות הבנק!</h3>", unsafe_allow_html=True)
                    unassigned_list_bank = [str(x).strip() for x in unassigned_bank["שם פעולה"].dropna().unique() if str(x).strip()]
                    
                    c1, c2 = st.columns(2)
                    with c1: selected_bank_biz = st.selectbox("בחר פעולה לא משויכת:", unassigned_list_bank, key="select_biz_bank")
                    with c2: selected_bank_cat = st.selectbox("שייך לקטגוריה:", [c for c in CATEGORIES if c not in ["עסק מוכר - סווג אוטומטית לפי מילון", "לא משויך"]], key="select_cat_bank")
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 שמור למילון ורענן (בנק)", type="primary", use_container_width=True):
                        try:
                            get_gspread_client().open_by_url(SPREADSHEET_URL).worksheet("מילון_עסקים").append_row([selected_bank_biz, selected_bank_cat])
                            load_data.clear()
                            st.success("שויך בהצלחה! העלה את הקובץ מחדש כדי לראות את העדכון.")
                        except Exception as e:
                            st.error(f"שגיאה: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                if bank_file.name.lower().endswith('.pdf'):
                    st.error("הקובץ נסרק, אך לא זוהו תנועות. ודא שזהו קובץ עו"ש תקין של מזרחי טפחות.")
        st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 5: ניהול מילון
    # -------------------------------------------------------------
    with tab5:
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown("<h3 style='color: #1e293b; margin-bottom: 10px;'>⚙️ ניהול מילון עסקים</h3>", unsafe_allow_html=True)
        
        if not df_dict.empty and len(df_dict.columns) >= 2:
            biz_col = df_dict.columns[0]
            cat_col = df_dict.columns[1]
            
            c_edit1, c_edit2 = st.columns([1, 1.2])
            with c_edit1:
                st.markdown("<h4 style='color: #3b82f6;'>✏️ עריכה או מחיקה</h4>", unsafe_allow_html=True)
                all_bizzes = sorted(df_dict[biz_col].dropna().astype(str).unique().tolist())
                edit_biz = st.selectbox("בחר עסק לעריכה:", all_bizzes)
                
                if edit_biz:
                    current_cat = df_dict[df_dict[biz_col] == edit_biz][cat_col].iloc[0]
                    st.write(f"משויך כרגע אל: **{current_cat}**")
                    valid_cats = [c for c in CATEGORIES if c not in ["עסק מוכר - סווג אוטומטית לפי מילון", "לא משויך"]]
                    default_idx = valid_cats.index(current_cat) if current_cat in valid_cats else 0
                    new_cat = st.selectbox("שנה לקטגוריה אחרת:", valid_cats, index=default_idx)
                    
                    btn1, btn2 = st.columns(2)
                    with btn1:
                        if st.button("💾 עדכן", type="primary", use_container_width=True):
                            try:
                                client = get_gspread_client()
                                wb = client.open_by_url(SPREADSHEET_URL)
                                dict_sheet = wb.worksheet("מילון_עסקים")
                                cell = dict_sheet.find(edit_biz, in_column=1)
                                if cell:
                                    dict_sheet.update_cell(cell.row, 2, new_cat)
                                    load_data.clear()
                                    st.success("עודכן!")
                                    st.rerun()
                            except Exception as e: st.error(f"שגיאה: {e}")
                    with btn2:
                        if st.button("🗑️ מחק", use_container_width=True):
                            try:
                                client = get_gspread_client()
                                wb = client.open_by_url(SPREADSHEET_URL)
                                dict_sheet = wb.worksheet("מילון_עסקים")
                                cell = dict_sheet.find(edit_biz, in_column=1)
                                if cell:
                                    dict_sheet.delete_rows(cell.row)
                                    load_data.clear()
                                    st.success("נמחק!")
                                    st.rerun()
                            except Exception as e: st.error(f"שגיאה: {e}")
            with c_edit2:
                st.markdown("<h4 style='color: #3b82f6;'>📚 המילון המלא</h4>", unsafe_allow_html=True)
                st.dataframe(df_dict, use_container_width=True, hide_index=True)
        else:
            st.info("המילון כרגע ריק.")
        st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error("שגיאת התחברות או ריצה. ודא שכתובת הגיליון נכונה בהגדרות.")
    st.write(e)
