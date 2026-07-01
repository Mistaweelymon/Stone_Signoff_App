import streamlit as st
from streamlit_drawable_canvas import st_canvas
import datetime
import requests
import json

st.set_page_config(page_title="Stone Shop Load-Out", layout="wide")

# 🔗 CONFIGURATION ENDPOINTS
FORM_URL = "https://docs.google.com/forms/d/1WWbNVnH7-9U3jEGjfMClNT-ZIKTXz1QZM73cCIapNJc/formResponse"

# 🔴 PASTE YOUR COPIED GOOGLE APPS SCRIPT WEB APP LINK RIGHT HERE BETWEEN THE QUOTES:
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzXVhdQUUDKs_f0Am-iMUYU-ErTph2-0ly4hgoq0Q7dwDR-SfMFBxH1VqSkxDsfbQmIhw/exec"

# --- INITIALIZE INTERNAL BLANK APP STATES ---
if "current_job_data" not in st.session_state:
    st.session_state.current_job_data = {
        "job_number": "", "subcontractor": "", "installer_name": "",
        "is_partial": "Yes - Full Job Leaving", "delayed_notes": "",
        "k_count": 0, "mb_count": 0, "ob_count": 0, "splash_count": 0, "other_count": 0,
        "stock_sinks": 0, "customer_sinks": 0, "sink_notes_input": "",
        "load_date": datetime.date.today().strftime("%Y-%m-%d")
    }

def reset_form():
    st.session_state.current_job_data = {
        "job_number": "", "subcontractor": "", "installer_name": "",
        "is_partial": "Yes - Full Job Leaving", "delayed_notes": "",
        "k_count": 0, "mb_count": 0, "ob_count": 0, "splash_count": 0, "other_count": 0,
        "stock_sinks": 0, "customer_sinks": 0, "sink_notes_input": "",
        "load_date": datetime.date.today().strftime("%Y-%m-%d")
    }
    if "canvas_key" not in st.session_state:
        st.session_state.canvas_key = "canvas_0"
    else:
        current_num = int(st.session_state.canvas_key.split("_")[1])
        st.session_state.canvas_key = f"canvas_{current_num + 1}"

# --- LIVE PULL FROM GOOGLE SHEET DRAFTS QUEUE ---
st.sidebar.title("📁 Scheduled Drafts Ledger")
search_query = st.sidebar.text_input("🔍 Search Jobs / Subcontractors", "").strip().lower()

saved_jobs_list = []
try:
    if WEBHOOK_URL != "PASTE_YOUR_APPS_SCRIPT_WEB_APP_URL_HERE":
        response = requests.get(WEBHOOK_URL, timeout=10)
        if response.status_code == 200:
            saved_jobs_list = response.json()
except Exception:
    st.sidebar.error("Could not fetch remote drafts layout.")

if saved_jobs_list:
    # Filter based on active sidebar query text
    filtered_jobs = [
        job for job in saved_jobs_list
        if search_query in str(job['job_number']).lower() or search_query in str(job['subcontractor']).lower()
    ]
    
    # Sort and group chronological order array mapping
    grouped_by_date = {}
    for job in filtered_jobs:
        date_str = job.get("load_date", datetime.date.today().strftime("%Y-%m-%d"))
        try:
            date_header = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d").strftime("%A, %B %d")
        except Exception:
            date_header = date_str
            
        if date_header not in grouped_by_date:
            grouped_by_date[date_header] = []
        grouped_by_date[date_header].append(job)
        
    if grouped_by_date:
        for date_header, jobs_list in grouped_by_date.items():
            st.sidebar.markdown(f"📅 **{date_header}**")
            for job in jobs_list:
                col_load, col_del = st.sidebar.columns([3, 1])
                # Load back to fields action
                if col_load.button(f"📄 {job['job_number']}", key=f"load_{job['job_number']}", use_container_width=True):
                    st.session_state.current_job_data = job
                    st.rerun()
                # Manual erase row target action
                if col_del.button("❌", key=f"del_{job['job_number']}"):
                    try:
                        requests.post(WEBHOOK_URL, json={"action": "delete_draft", "job_number": job['job_number']})
                        st.sidebar.success(f"Erased {job['job_number']}")
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error("Failed to delete draft row.")
            st.sidebar.markdown("---")
    else:
        st.sidebar.warning("No matches found.")
else:
    st.sidebar.info("No active drafts found on spreadsheet queue.")

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
    curr_dt = st.session_state.current_job_data.get("load_date", datetime.date.today().strftime("%Y-%m-%d"))
    try:
        parsed_dt = datetime.datetime.strptime(curr_dt[:10], "%Y-%m-%d").date()
    except Exception:
        parsed_dt = datetime.date.today()
    job_load_date = st.date_input("Scheduled Load-Out Date", value=parsed_dt)

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

# --- ACTION BUTTONS FOOTER ---
st.markdown("---")
btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 4])

# Button 1: Save Draft via Webhook to Spreadsheet
if btn_col1.button("💾 Save for Future Job", use_container_width=True):
    if not job_number:
        st.error("Please fill out a 'Job Name / Number' before choosing Save for Future.")
    elif WEBHOOK_URL == "PASTE_YOUR_APPS_SCRIPT_WEB_APP_URL_HERE":
        st.error("Please configure your deployed Webhook URL at the top of the file script.")
    else:
        payload = {
            "action": "save_draft", "job_number": job_number, "subcontractor": subcontractor, "installer_name": installer_name,
            "is_partial": is_partial, "delayed_notes": delayed_notes, "k_count": k_count, "mb_count": mb_count,
            "ob_count": ob_count, "splash_count": splash_count, "other_count": other_count, "stock_sinks": stock_sinks,
            "customer_sinks": customer_sinks, "sink_notes_input": sink_notes_input, "load_date": job_load_date.strftime("%Y-%m-%d")
        }
        try:
            # Drop current state first before wiping if overwritten
            requests.post(WEBHOOK_URL, json={"action": "delete_draft", "job_number": job_number})
            requests.post(WEBHOOK_URL, json=payload)
            st.toast(f"Draft {job_number} pushed to Sheet queue!", icon="💾")
            reset_form()
            st.rerun()
        except Exception as e:
            st.error(f"Network delivery failure: {e}")

# Button 2: Manual Clear Screen
if btn_col2.button("🧹 Clear Form Screen", use_container_width=True):
    reset_form()
    st.rerun()

# Button 3: Submit Complete Sheet (Form post + remote cleanup combo)
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
                    # Clean up the draft tab row since the job is now finalized
                    if WEBHOOK_URL != "PASTE_YOUR_APPS_SCRIPT_WEB_APP_URL_HERE":
                        requests.post(WEBHOOK_URL, json={"action": "delete_draft", "job_number": job_number})
                    
                    st.success(f"🎉 Success! Job {job_number} load-out sheet saved.")
                    st.balloons()
                    reset_form()
                    st.rerun()
                else:
                    st.error(f"Form submission returned status code: {response.status_code}")
                    
        except Exception as e:
            st.error(f"An error occurred while saving: {e}")
