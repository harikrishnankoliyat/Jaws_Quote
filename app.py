import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
import os
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Jaws Africa Safari Planner", layout="wide")

# --- CSS: FORCED DESKTOP SCALING ---
st.markdown("""
    <style>
    /* 1. REMOVE STREAMLIT DEFAULTS */
    a.header-anchor { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }
    
    /* 2. FORCED DESKTOP STYLE (LARGE BY DEFAULT) */
    .white-total-box {
        background-color: #FFFFFF !important;
        padding: 40px 20px !important; 
        border-radius: 30px !important;
        border: 4px solid #000000 !important;
        text-align: center !important;
        margin: 30px auto !important;
        width: 95% !important; 
        box-shadow: 0px 20px 50px rgba(0,0,0,0.2) !important;
        display: block !important;
    }

    .total-title-text {
        color: #000000 !important;
        font-family: 'Calibri', sans-serif !important;
        font-weight: 900 !important;
        font-size: 55px !important; /* Adjusted to fit one line */
        margin-bottom: 5px !important;
        display: block !important;
        white-space: nowrap !important;
    }

    .per-person-text {
        color: #444444 !important; 
        font-family: 'Calibri', sans-serif !important; 
        font-weight: bold !important;
        font-size: 32px !important;
        display: block !important;
    }

    /* 3. MOBILE RESPONSIVE OVERRIDE */
    @media only screen and (max-width: 800px) {
        .white-total-box {
            padding: 30px 10px !important;
            width: 100% !important;
            border: 2px solid #000000 !important;
        }
        .total-title-text { font-size: 26px !important; white-space: normal !important;}
        .per-person-text { font-size: 18px !important; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("🦁 Jaws Africa - Masai Mara 2026")

# --- DATA LOADING ---
def load_data():
    file_path = "Master Quotation Details 2026_V0.xlsx"
    if not os.path.exists(file_path):
        st.error("Excel file not found!")
        st.stop()
    
    xls = pd.ExcelFile(file_path)
    df_acc = pd.read_excel(xls, 'Accommodation Cost (Adults)')
    df_park = pd.read_excel(xls, 'Park Fees')
    df_comm = pd.read_excel(xls, 'Jaws Africa Commission')
    df_veh = pd.read_excel(xls, 'Vehicle Cost') 
    
    for df, start, end in [(df_acc, 'Date From', 'Date To'), (df_park, 'Dates From', 'Dates To')]:
        df[start] = pd.to_datetime(df[start])
        df[end] = pd.to_datetime(df[end])
    return df_acc, df_park, df_comm, df_veh

df_acc, df_park, df_comm, df_veh = load_data()

# --- SIDEBAR ---
st.sidebar.header("1. GLOBAL TRIP DATA")
start_date = st.sidebar.date_input("Start Date", datetime(2026, 6, 14))
adults = st.sidebar.number_input("Total Adults", min_value=1, value=2)
v_in_days = st.sidebar.number_input("Vehicle Days (Inside Mara)", value=0)
v_out_days = st.sidebar.number_input("Vehicle Days (Outside Mara)", value=0)
extra_chg = st.sidebar.number_input("Additional Charges ($)", value=0)

if 'lodge_count' not in st.session_state:
    st.session_state.lodge_count = 1

lodge_inputs = []
for i in range(st.session_state.lodge_count):
    with st.sidebar.container(border=True):
        st.markdown(f"**Lodge #{i+1}**")
        n = st.number_input("Nights", min_value=1, value=1, key=f"n{i}")
        rt = st.selectbox("Type", sorted(df_acc['Room Type'].unique()), key=f"rt{i}")
        p = st.selectbox("Property", df_acc[df_acc['Room Type'] == rt]['Property'].unique(), key=f"p{i}")
        occ = st.selectbox("Occupancy", ["Single", "Double", "Triple"], index=1, key=f"o{i}")
        lodge_inputs.append({"nights": n, "prop": p, "rtype": rt, "occ": occ})

if st.sidebar.button("+ Add Lodge"):
    st.session_state.lodge_count += 1
    st.rerun()

# --- CALCULATION ---
if st.button("GENERATE CALCULATION", type="primary"):
    try:
        acc_total, park_total, day_offset = 0, 0, 0
        acc_report, park_report = "", ""
        start_dt = pd.to_datetime(start_date)

        for lodge in lodge_inputs:
            occ_col = f"{lodge['occ']} (Cost Per Person/Per Night)"
            for _ in range(lodge['nights']):
                cur_date = start_dt + timedelta(days=day_offset)
                a_mask = (df_acc['Property']==lodge['prop']) & (df_acc['Room Type']==lodge['rtype']) & \
                         (df_acc['Date From']<=cur_date) & (df_acc['Date To']>=cur_date)
                a_rate = round(float(df_acc[a_mask].iloc[0][occ_col]))
                
                # Check column name for Park Fees sheet
                p_mask = (df_park['Dates From']<=cur_date) & (df_park['Dates To']>=cur_date) & \
                         (df_park['Travellers  Category']=='Adult')
                p_rate = float(df_park[p_mask].iloc[0]['Park Fee Per Night Per Person in USD'])
                
                acc_total += (a_rate * adults)
                park_total += (p_rate * adults)
                acc_report += f"{cur_date.date()} | {lodge['prop'][:12]:<12} | {adults} Pax x ${a_rate:<5} = ${a_rate*adults}\n"
                park_report += f"{cur_date.date()} | Park Fee    | {adults} Pax x ${p_rate:<5} = ${p_rate*adults}\n"
                day_offset += 1

        v_out_rate = float(df_veh[df_veh['Location'] == 'Anywhere Outside Mara']['Cost in USD/Per Day'].iloc[0])
        v_in_rate = float(df_veh[df_veh['Location'] == 'Only Masai Mara']['Cost in USD/Per Day'].iloc[0])
        
        v_in_subtotal = v_in_days * v_in_rate
        v_out_subtotal = v_out_days * v_out_rate
        v_total = v_in_subtotal + v_out_subtotal
        
        comm_rate = float(df_comm.iloc[0]['Commission Per Person (USD)'])
        comm_total = comm_rate * adults
        grand_total = acc_total + park_total + v_total + comm_total + extra_chg

        # --- BREAKDOWN OUTPUTS ---
        st.markdown("### 1. ACCOMMODATION")
        st.code(f"{acc_report}TOTAL ACCOMMODATION: ${acc_total:,.2f}", language="text")
        
        st.markdown("### 2. PARK FEES")
        st.code(f"{park_report}TOTAL PARK FEES: ${park_total:,.2f}", language="text")
        
        st.markdown("### 3. VEHICLE")
        v_report = f"Inside Mara: {v_in_days} Days x ${v_in_rate:,.2f} = ${v_in_subtotal:,.2f}\n"
        v_report += f"Outside Mara: {v_out_days} Days x ${v_out_rate:,.2f} = ${v_out_subtotal:,.2f}\n"
        v_report += f"TOTAL VEHICLE: ${v_total:,.2f}"
        st.code(v_report, language="text")

        st.markdown("### 4. COMMISSION")
        st.code(f"{adults} Adults x ${comm_rate:,.2f} = ${comm_total:,.2f}", language="text")
        
        st.markdown("### 5. ADDITIONAL CHARGES")
        st.code(f"Total Extra Charges: ${extra_chg:,.2f}", language="text")

        st.divider()
        
        # --- THE FORCED MASSIVE BOX ---
        st.markdown(f"""
            <div class="white-total-box">
                <span class="total-title-text">TOTAL TRIP COST: ${grand_total:,.2f}</span>
                <span class="per-person-text">COST PER PERSON: ${grand_total/adults:,.2f}</span>
            </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Calculation Error: {e}")