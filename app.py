import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
import os

# Set page to wide mode
st.set_page_config(page_title="Jaws Africa Safari Planner", layout="wide")

# --- CSS INJECTION: DISABLE LINK ICONS & STYLE TOTALS ---
st.markdown("""
    <style>
    /* Hide the link/anchor icons next to headers */
    .viewerBadge_container__1QSob { display: none; }
    button.step-down, button.step-up { display: none; }
    a.header-anchor { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }
    
    /* Global font for Calibri feel */
    html, body, [class*="css"] { font-family: 'Calibri', sans-serif; }
    </style>
""", unsafe_allow_html=True)

st.title("🦁 Jaws Africa - Masai Mara 2026")

# Load Data
@st.cache_data
def load_data():
    file_path = "Master Quotation Details 2026_V0.xlsx"
    if not os.path.exists(file_path):
        return None, None, None
    xls = pd.ExcelFile(file_path)
    df_acc = pd.read_excel(xls, 'Accommodation Cost (Adults)')
    df_park = pd.read_excel(xls, 'Park Fees')
    df_comm = pd.read_excel(xls, 'Jaws Africa Commission')
    
    for df, start, end in [(df_acc, 'Date From', 'Date To'), (df_park, 'Dates From', 'Dates To')]:
        df[start] = pd.to_datetime(df[start])
        df[end] = pd.to_datetime(df[end])
    return df_acc, df_park, df_comm

df_acc, df_park, df_comm = load_data()

if df_acc is None:
    st.error("Excel file 'Master Quotation Details 2026_V0.xlsx' not found!")
    st.stop()

# --- SIDEBAR: INPUTS ---
st.sidebar.header("1. GLOBAL TRIP DATA")
start_date = st.sidebar.date_input("Start Date", datetime(2026, 6, 14))
adults = st.sidebar.number_input("Total Adults", min_value=1, value=2)
v_in = st.sidebar.number_input("Vehicle Days (Inside Mara)", value=3)
v_out = st.sidebar.number_input("Vehicle Days (Outside Mara)", value=2)
extra_chg = st.sidebar.number_input("Additional Charges ($)", value=0)

st.sidebar.markdown("---")
st.sidebar.header("2. ACCOMMODATION DATA")

if 'lodge_count' not in st.session_state:
    st.session_state.lodge_count = 1

lodge_inputs = []
for i in range(st.session_state.lodge_count):
    with st.sidebar.container(border=True):
        st.markdown(f"**Lodge #{i+1}**")
        n = st.number_input("Nights", min_value=1, value=2, key=f"n{i}")
        rt = st.selectbox("Type", sorted(df_acc['Room Type'].unique()), key=f"rt{i}")
        props = df_acc[df_acc['Room Type'] == rt]['Property'].unique()
        p = st.selectbox("Property", props, key=f"p{i}")
        occ = st.selectbox("Occupancy", ["Single", "Double", "Triple"], index=1, key=f"o{i}")
        lodge_inputs.append({"nights": n, "prop": p, "rtype": rt, "occ": occ})

if st.sidebar.button("+ Add Accommodation"):
    st.session_state.lodge_count += 1
    st.rerun()

# --- MAIN AREA: CALCULATION ---
if st.button("GENERATE CALCULATION", type="primary"):
    acc_total, park_total, day_offset = 0, 0, 0
    acc_report, park_report = "", ""
    start_dt = pd.to_datetime(start_date)

    for lodge in lodge_inputs:
        occ_col = f"{lodge['occ']} (Cost Per Person/Per Night)"
        for _ in range(lodge['nights']):
            cur_date = start_dt + timedelta(days=day_offset)
            
            # Acc Rate (Rounded)
            a_mask = (df_acc['Property']==lodge['prop']) & (df_acc['Room Type']==lodge['rtype']) & \
                     (df_acc['Date From']<=cur_date) & (df_acc['Date To']>=cur_date)
            a_rate = round(float(df_acc[a_mask].iloc[0][occ_col]))
            
            # Park Fee
            p_mask = (df_park['Dates From']<=cur_date) & (df_park['Dates To']>=cur_date) & \
                     (df_park['Travellers  Category']=='Adult')
            p_rate = float(df_park[p_mask].iloc[0]['Park Fee Per Night Per Person in USD'])
            
            acc_total += (a_rate * adults)
            park_total += (p_rate * adults)
            
            acc_report += f"{cur_date.date()} | {lodge['prop'][:12]:<12} | {adults} Pax x ${a_rate:<5} = ${a_rate*adults}\n"
            park_report += f"{cur_date.date()} | Park Fee    | {adults} Pax x ${p_rate:<5} = ${p_rate*adults}\n"
            day_offset += 1

    v_in_total, v_out_total = v_in * 200, v_out * 230
    v_total = v_in_total + v_out_total
    comm_total = 150 * adults
    grand_total = acc_total + park_total + v_total + comm_total + extra_chg

    # --- DISPLAY BREAKDOWN ---
    
    
    st.markdown("### 1. ACCOMMODATION")
    st.code(f"{acc_report}TOTAL ACCOMMODATION: ${acc_total:,.2f}", language="text")

    st.markdown("### 2. PARK FEES")
    st.code(f"{park_report}TOTAL PARK FEES: ${park_total:,.2f}", language="text")

    st.markdown("### 3. VEHICLE")
    v_report = f"Inside Mara : {v_in} Days x $200 = ${v_in_total}\n"
    v_report += f"Outside Mara: {v_out} Days x $230 = ${v_out_total}\n"
    v_report += f"TOTAL VEHICLE COST: ${v_total:,.2f}"
    st.code(v_report, language="text")

    st.markdown("### 4. JAWS COMMISSION")
    c_report = f"{adults} Adults x $150 per person\n"
    c_report += f"TOTAL COMMISSION: ${comm_total:,.2f}"
    st.code(c_report, language="text")

    st.markdown("### 5. ADDITIONAL CHARGES")
    st.code(f"Total Extra Charges: ${extra_chg:,.2f}", language="text")

    st.divider()
    
    # Final Totals with White Background
    st.markdown(f"""
        <div style="background-color: transparent; padding: 30px; border-radius: 15px; border: 1px solid #DDDDDD; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
            <h1 style="color: white; font-family: 'Calibri', sans-serif; margin-bottom: 0px;">TOTAL TRIP COST: ${grand_total:,.2f}</h1>
            <h3 style="color: #555555; font-family: 'Calibri', sans-serif; margin-top: 5px;">COST PER PERSON: ${grand_total/adults:,.2f}</h3>
        </div>
    """, unsafe_allow_html=True)