import streamlit as st
from streamlit_drawable_canvas import st_canvas
import datetime
import requests
import json

st.set_page_config(page_title="Stone Shop Load-Out", layout="wide")

# Hardcoded direct public form gateway link
FORM_URL = "https://docs.google.com/forms/d/1WWbNVnH7-9U3jEGjfMClNT-ZIKTXz1QZM73cCIapNJc/formResponse"

# --- INITIALIZE SESSION STATE MEMORY ---
if "saved_jobs" not in st.session_state:
    st.session_state.saved_jobs = {}

if "current_job_data" not in st.session_state:
    st.session_state.current_job_data = {
        "job_number": "", "subcontractor": "", "installer_name": "",
        "is_partial": "Yes - Full Job Leaving", "delayed_notes": "",
        "k_count": 0, "mb_count": 0, "ob_count": 0, "splash_count": 0, "other_count": 0,
        "stock_sinks": 0, "customer_sinks": 0, "sink_notes_input": "",
        "load_date": datetime.date.today()  # Default calendar selection to today
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

# --- SIDEBAR: DATE-CATEGORIZED & SEARCHABLE FUTURE JOBS ---
st.sidebar.title("📁 Scheduled Drafts")

# Search Bar Interface
search_query = st.sidebar.text_input("🔍 Search Jobs / Subcontractors", "").strip().lower()

if st.session_state.saved_jobs:
    # 1. Filter list based on search bar text matching Job or Subcontractor
    filtered_jobs = {
        name: data for name, data in st.session_state.saved_jobs.items()
        if search_query in name.lower() or search_query in data.get("subcontractor", "").lower()
    }
    
    # 2. Group the filtered jobs by their assigned scheduled dates
    grouped_by_date = {}
    for name, data in filtered_jobs.items():
        d_obj = data.get("load_date", datetime.date.today())
        # Format the date nicely as a header string (e.g., "Thursday, July 2")
        date_str = d_obj.strftime("%A, %B %d")
        if date_str not in grouped_by_date:
            grouped_by_date[date_str] = []
        grouped_by_date[date_str].append((name, data))
        
    # 3. Render the grouped calendar slots in chronological order
    if grouped_by_date:
        for date_header, jobs_list in grouped_by_date.items():
            st.sidebar.markdown(f"📅 **{date_header}**")
            for name, data in jobs_list:
                col_load, col_del = st.sidebar.columns([3, 1])
                # Load action
                if col_load.button(f"📄 {name}", key=f"load_{name}", use_container_width=True):
                    st.session_state.current_job_data = st.session_state.saved_jobs[name].copy()
                    st.rerun()
                # Delete action
                if col_del.button("❌", key=f"del_{name}"):
                    del st.session_state.saved_jobs[name]
                    st.sidebar.success(f"Removed {name}")
                    st.rerun()
            st.sidebar.markdown("---")
    else:
        st.sidebar.warning("No scheduled jobs match your search.")
else:
    st.sidebar.info("No saved jobs yet. Use the fields on the right to draft one.")

# --- MAIN FORM INTERFACE ---
st.title("📱 Job Load-Out & Sign-Off")
st.write("Complete this form alongside the subcontractor during truck loading.")

# --- SECTION 1: JOB DETAILS & CALENDAR ROUTING ---
st.header("1. Job Details")
col_j1, col_j2 = st.columns([2, 1])
with col_j1:
    job_number = st.text_input("Job Name / Number", value=st.session_state.current_job_data["job_number"])
    subcontractor = st.text_input("Subcontractor Company", value=st.session_state.current_job_data["subcontractor"])
with col_j2:
    # Calendar date selector widget
    saved_date = st.session_state.current_job_data.get("load_date", datetime.date.today())
    job_load_date = st.date_input("Scheduled Load-Out Date", value=saved_date)

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
    k_count = st.number_input("Kitchen Pieces", min_value=0, step=1, value=st.session_state.current_job_data["k_count"])
    mb_count = st.number_input("Primary / Master Bath Pieces", min_value=0, step=1, value=st.session_state.current_job_data["mb_count"])
    ob_count = st.number_input("Additional Bath Pieces", min_value=0, step=1, value=st.session_state.current_job_data["ob_count"])
with col2:
    splash_count = st.number_input("Loose Splash Pieces", min_value=0, step=1, value=st.session_state.current_job_data["splash_count"])
    other_count = st.number_input("Other (Fireplace, Laundry, etc.)", min_value=0, step=1, value=st.session_state.current_job_data["other_count"])

total_pieces = k_count + mb_count + ob_count + splash_count + other_count
st.metric(label="Total Pieces Checked Onto Truck", value=total_pieces)

# --- SECTION 4: SINK VERIFICATION ---
st.header("4. Sink Accounting")
col3, col4 = st.columns(2)
with col3:
    stock_sinks = st.number_input("Shop Stock Sinks Loaded", min_value=0, step=1, value=st.session_state.current_job_data["stock_sinks"])
with col4:
    customer_sinks = st.number_input("Customer-Provided Sinks Loaded", min_value=0, step=1, value=st.session_state.current_job_data["customer_sinks"])

sink_notes_input = st.text_input("Sink Notes (e.g., missing sinks, specific model types, or description)", value=st.session_state.current_job_data["sink_notes_input"])
sink_notes_final = "None" if not sink_notes_input else sink_notes_input

sinks_notes = f"Stock Sinks: {stock_sinks} | Customer Sinks: {customer_sinks} | Sink Notes: {sink_notes_final}"

# --- SECTION 5: SIGNATURE ---
st.header("5. Custody Transfer & Sign-Off")
st.warning(
    "Installer Acknowledgment: By signing below, I confirm that I have physically counted and inspected the loaded items. "
    "I verify that any delayed areas are explicitly left behind, and everything else is present and loaded in good condition."
)

st.write("Lead Installer Signature:")
if "canvas_key" not in st.session_state:
    st.session_state.canvas_key = "canvas_0"

canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.3)",
    stroke_width=3,
    stroke_color="#000000",
    background_color="#eee",
    height=150,
    drawing_mode="freedraw",
    key=st.session_state.canvas_key,
)

# --- ACTION BUTTONS FOOTER ---
st.markdown("---")
btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 4])

# Button 1: Save Draft for Future Date Group
if btn_col1.button("💾 Save for Future Job", use_container_width=True):
    if not job_number:
        st.error("Please fill out a 'Job Name / Number' before choosing Save for Future.")
    else:
        # Cache snapshot mapped to the specific calendar date selected
        st.session_state.saved_jobs[job_number] = {
            "job_number": job_number, "subcontractor": subcontractor, "installer_name": installer_name,
            "is_partial": is_partial, "delayed_notes": delayed_notes,
            "k_count": k_count, "mb_count": mb_count, "ob_count": ob_count, "splash_count": splash_count, "other_count": other_count,
            "stock_sinks": stock_sinks, "customer_sinks": customer_sinks, "sink_notes_input": sink_notes_input,
            "load_date": job_load_date
        }
        st.toast(f"Saved to {job_load_date.strftime('%b %d')}: {job_number}!", icon="💾")
        reset_form()
        st.rerun()

# Button 2: Manual Clear Screen
if btn_col2.button("🧹 Clear Form Screen", use_container_width=True):
    reset_form()
    st.rerun()

# Button 3: Submit Complete Sheet
if btn_col3.button("Submit Load-Out Sheet", type="primary", use_container_width=True):
    if not job_number or not installer_name or not subcontractor:
        st.error("Please fill out the Job Number, Subcontractor, and Installer Name before submitting.")
    elif not canvas_result.json_data or len(canvas_result.json_data["objects"]) == 0:
        st.error("The Lead Installer must sign the signature box before submitting.")
    else:
        try:
            with st.spinner("Saving data securely..."):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sig_data = json.dumps(canvas_result.json_data["objects"])
                
                # Appends the final scheduled layout to the data package
                text_summary = (
                    f"Job: {job_number} | "
                    f"Co: {subcontractor} | "
                    f"Name: {installer_name} | "
                    f"Total Loaded: {total_pieces} | "
                    f"Breakdown: [K:{k_count}, MB:{mb_count}, Bath:{ob_count}, Splash:{splash_count}, Other:{other_count}] | "
                    f"Sinks: {sinks_notes} | "
                    f"Delayed: {delayed_notes}"
                )
                
                form_data = {
                    "entry.2095053729": text_summary,  
                    "entry.2107411274": sig_data       
                }
                
                headers = {
                    "Referer": FORM_URL.replace("/formResponse", "/viewform"),
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                
                response = requests.post(FORM_URL, data=form_data, headers=headers)
                
                if response.status_code == 200:
                    if job_number in st.session_state.saved_jobs:
                        del st.session_state.saved_jobs[job_number]
                    
                    st.success(f"🎉 Success! Job {job_number} load-out sheet saved.")
                    st.balloons()
                    reset_form()
                    st.rerun()
                else:
                    st.error(f"Form submission returned status code: {response.status_code}")
                    
        except Exception as e:
            st.error(f"An error occurred while saving: {e}")
