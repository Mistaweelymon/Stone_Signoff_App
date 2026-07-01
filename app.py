import streamlit as st
from streamlit_drawable_canvas import st_canvas
import datetime
import requests
import json

st.set_page_config(page_title="Stone Shop Load-Out", layout="wide")

# 🔗 MAIN FORM GATEWAY
FORM_URL = "https://docs.google.com/forms/d/1WWbNVnH7-9U3jEGjfMClNT-ZIKTXz1QZM73cCIapNJc/formResponse"

# 📅 THE MASTER SCHEDULE DESK
# You can pre-type your upcoming runs right here. The crew will see them on their phones instantly!
PRE_LOADED_SCHEDULE = {
    "Job 101 - Smith Residence": {
        "subcontractor": "Apex Installers", "k_count": 3, "mb_count": 2, "ob_count": 1,
        "splash_count": 4, "other_count": 0, "stock_sinks": 2, "customer_sinks": 1, 
        "sink_notes_input": "CP Blanco stainless steel sink provided by homeowner", "load_date": "2026-07-02"
    },
    "Job 102 - Granite Towers Apt 4B": {
        "subcontractor": "Triangle Stone Crews", "k_count": 5, "mb_count": 0, "ob_count": 3,
        "splash_count": 0, "other_count": 1, "stock_sinks": 4, "customer_sinks": 0, 
        "sink_notes_input": "All shop stock vanity bowls", "load_date": "2026-07-02"
    }
}

# --- INITIALIZE APP STORAGE ---
if "current_job_data" not in st.session_state:
    st.session_state.current_job_data = {
        "job_number": "", "subcontractor": "", "installer_name": "",
        "is_partial": "Yes - Full Job Leaving", "delayed_notes": "",
        "k_count": 0, "mb_count": 0, "ob_count": 0, "splash_count": 0, "other_count": 0,
        "stock_sinks": 0, "customer_sinks": 0, "sink_notes_input": "",
        "load_date": datetime.date.today()
    }

def reset_form():
    st.session_state.current_job_data = {
        "job_number": "", "subcontractor": "", "installer_name": "",
        "is_partial": "Yes - Full Job Leaving", "delayed_notes": "",
        "k_count": 0, "mb_count": 0, "ob_count": 0, "splash_count": 0, "other_count": 0,
        "stock_sinks": 0, "customer_sinks": 0, "sink_notes_input": "",
        "load_date": datetime.date.today()
    }
    if "canvas_key" not in st.session_state:
        st.session_state.canvas_key = "canvas_0"
    else:
        current_num = int(st.session_state.canvas_key.split("_")[1])
        st.session_state.canvas_key = f"canvas_{current_num + 1}"

# --- SIDEBAR: SEARCHABLE WORK SCHEDULE ---
st.sidebar.title("📁 Scheduled Jobs Ledger")
search_query = st.sidebar.text_input("🔍 Search Pre-Typed Schedule", "").strip().lower()

# Group our hardcoded master dictionary chronologically by date strings
grouped_schedule = {}
for name, data in PRE_LOADED_SCHEDULE.items():
    if search_query in name.lower() or search_query in data["subcontractor"].lower():
        # Clean calendar formatting for the section layout headers
        try:
            d_obj = datetime.datetime.strptime(data["load_date"], "%Y-%m-%d")
            date_header = d_obj.strftime("%A, %B %d")
        except Exception:
            date_header = "Scheduled Run"
            
        if date_header not in grouped_schedule:
            grouped_schedule[date_header] = []
        grouped_schedule[date_header].append((name, data))

if grouped_schedule:
    for date_header, jobs in grouped_schedule.items():
        st.sidebar.markdown(f"📅 **{date_header}**")
        for name, data in jobs:
            if st.sidebar.button(f"📄 {name}", key=f"sched_{name}", use_container_width=True):
                # Map the cached data array elements straight to fields
                st.session_state.current_job_data = {
                    "job_number": name,
                    "subcontractor": data["subcontractor"],
                    "installer_name": "",
                    "is_partial": "Yes - Full Job Leaving",
                    "delayed_notes": "",
                    "k_count": data["k_count"],
                    "mb_count": data["mb_count"],
                    "ob_count": data["ob_count"],
                    "splash_count": data["splash_count"],
                    "other_count": data["other_count"],
                    "stock_sinks": data["stock_sinks"],
                    "customer_sinks": data["customer_sinks"],
                    "sink_notes_input": data["sink_notes_input"],
                    # Wrap default parsed time formatting checks safely
                    "load_date": datetime.datetime.strptime(data["load_date"], "%Y-%m-%d").date()
                }
                st.rerun()
        st.sidebar.markdown("---")
else:
    st.sidebar.info("No matching schedule items found.")

# --- MAIN FORM INTERFACE ---
st.title("📱 Job Load-Out & Sign-Off")
st.write("Complete this form alongside the subcontractor during truck loading.")

# --- SECTION 1: JOB INFO ---
st.header("1. Job Details")
col_j1, col_j2 = st.columns([2, 1])
with col_j1:
    job_number = st.text_input("Job Name / Number", value=st.session_state.current_job_data["job_number"])
    subcontractor = st.text_input("Subcontractor Company", value=st.session_state.current_job_data["subcontractor"])
with col_j2:
    job_load_date = st.date_input("Scheduled Load-Out Date", value=st.session_state.current_job_data["load_date"])

installer_name = st.text_input("Lead Installer Name", value=st.session_state.current_job_data["installer_name"])

# --- SECTION 2: DELAYED ITEMS ---
st.header("2. Delayed Items")
default_idx = 0 if st.session_state.current_job_data["is_partial"] == "Yes - Full Job Leaving" else 1
is_partial = st.radio("Is the entire job leaving the shop today?", ["Yes - Full Job Leaving", "No - Partial Shipment"], index=default_idx)

delayed_notes = "N/A"
if is_partial == "No - Partial Shipment":
    delayed_notes = st.text_area("List rooms or pieces remaining at the shop:", value=st.session_state.current_job_data["delayed_notes"])

# --- SECTION 3: PIECE COUNTS ---
st.header("3. Physical Piece Count Loaded")
col1, col2 = st.columns(2)
with col1:
    k_count = st.number_input("Kitchen Pieces", min_value=0, step=1, value=int(st.session_state.current_job_data["k_count"]))
    mb_count = st.number_input("Primary / Master Bath Pieces", min_value=0, step=1, value=int(st.session_state.current_job_data["mb_count"]))
    ob_count = st.number_input("Additional Bath Pieces", min_value=0, step=1, value=int(st.session_state.current_job_data["ob_count"]))
with col2:
    splash_count = st.number_input("Loose Splash Pieces", min_value=0, step=1, value=int(st.session_state.current_job_data["splash_count"]))
    other_count = st.number_input("Other (Fireplace, Laundry, etc.)", min_value=0, step=1, value=int(st.session_state.current_job_data["other_count"]))

total_pieces = k_count + mb_count + ob_count + splash_count + other_count
st.metric(label="Total Pieces Checked Onto Truck", value=total_pieces)

# --- SECTION 4: SINK ACCOUNTING ---
st.header("4. Sink Accounting")
col3, col4 = st.columns(2)
with col3:
    stock_sinks = st.number_input("Shop Stock Sinks Loaded", min_value=0, step=1, value=int(st.session_state.current_job_data["stock_sinks"]))
with col4:
    customer_sinks = st.number_input("Customer-Provided Sinks Loaded", min_value=0, step=1, value=int(st.session_state.current_job_data["customer_sinks"]))

sink_notes_input = st.text_input("Sink Notes (e.g., missing sinks, specific model types, or description)", value=st.session_state.current_job_data["sink_notes_input"])
sink_notes_final = "None" if not sink_notes_input else sink_notes_input

sinks_notes = f"Stock Sinks: {stock_sinks} | Customer Sinks: {customer_sinks} | Sink Notes: {sink_notes_final}"

# --- SECTION 5: SIGNATURE ---
st.header("5. Custody Transfer & Sign-Off")
st.warning("Installer Acknowledgment: By signing below, I confirm that I have physically counted and inspected the loaded items.")

st.write("Lead Installer Signature:")
if "canvas_key" not in st.session_state:
    st.session_state.canvas_key = "canvas_0"

canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.3)", stroke_width=3, stroke_color="#000000",
    background_color="#eee", height=150, drawing_mode="freedraw", key=st.session_state.canvas_key,
)

# --- ACTION FOOTER BUTTONS ---
st.markdown("---")
btn_col1, btn_col2 = st.columns([3, 5])

if btn_col1.button("🧹 Clear / Reset Screen", use_container_width=True):
    reset_form()
    st.rerun()

if btn_col2.button("Submit Load-Out Sheet", type="primary", use_container_width=True):
    if not job_number or not installer_name or not subcontractor:
        st.error("Please fill out the Job Number, Subcontractor, and Installer Name before submitting.")
    elif not canvas_result.json_data or len(canvas_result.json_data["objects"]) == 0:
        st.error("The Lead Installer must sign the signature box before submitting.")
    else:
        try:
            with st.spinner("Saving data securely..."):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sig_data = json.dumps(canvas_result.json_data["objects"])
                
                text_summary = (
                    f"Job: {job_number} | Co: {subcontractor} | Name: {installer_name} | Total Loaded: {total_pieces} | "
                    f"Breakdown: [K:{k_count}, MB:{mb_count}, Bath:{ob_count}, Splash:{splash_count}, Other:{other_count}] | "
                    f"Sinks: {sinks_notes} | Delayed: {delayed_notes}"
                )
                
                form_data = {"entry.2095053729": text_summary, "entry.2107411274": sig_data}
                headers = {
                    "Referer": FORM_URL.replace("/formResponse", "/viewform"),
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                response = requests.post(FORM_URL, data=form_data, headers=headers)
                
                if response.status_code == 200:
                    st.success(f"🎉 Success! Job {job_number} load-out sheet saved.")
                    st.balloons()
                    reset_form()
                    st.rerun()
                else:
                    st.error(f"Form submission returned status code: {response.status_code}")
                    
        except Exception as e:
            st.error(f"An error occurred while saving: {e}")
