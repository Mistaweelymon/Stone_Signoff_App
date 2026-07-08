import streamlit as st
from streamlit_drawable_canvas import st_canvas
import datetime
import requests
from sqlalchemy import text
import json

st.set_page_config(page_title="Stone Shop Load-Out", layout="wide")

# 🔗 MAIN FORM ENDPOINT
FORM_URL = "https://docs.google.com/forms/d/1WWbNVnH7-9U3jEGjfMClNT-ZIKTXz1QZM73cCIapNJc/formResponse"

# --- SHARED CLOUD DATABASE CONFIGURATION ---
def get_db_connection():
    return st.connection("sqlite_project", type="sql")

def init_db():
    conn = get_db_connection()
    with conn.session as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS drafts (
                job_number TEXT PRIMARY KEY,
                subcontractor TEXT,
                installer_name TEXT,
                is_partial TEXT,
                delayed_notes TEXT,
                k_count INTEGER,
                mb_count INTEGER,
                ob_count INTEGER,
                splash_count INTEGER,
                other_count INTEGER,
                stock_sinks INTEGER,
                customer_sinks INTEGER,
                sink_notes_input TEXT,
                load_date TEXT
            )
        """))
        session.commit()

init_db()

# --- FORM STATE MEMORY BUFFER ---
# We store values here first so we can modify them freely without breaking Streamlit's widget keys
if "form_buffer" not in st.session_state:
    st.session_state.form_buffer = {
        "job_number": "", "subcontractor": "", "installer_name": "",
        "is_partial": "Yes - Full Job Leaving", "delayed_notes": "N/A",
        "k_count": 0, "mb_count": 0, "ob_count": 0, "splash_count": 0, "other_count": 0,
        "stock_sinks": 0, "customer_sinks": 0, "sink_notes_input": "",
        "load_date": datetime.date.today().strftime("%Y-%m-%d")
    }

def reset_form():
    st.session_state.form_buffer = {
        "job_number": "", "subcontractor": "", "installer_name": "",
        "is_partial": "Yes - Full Job Leaving", "delayed_notes": "N/A",
        "k_count": 0, "mb_count": 0, "ob_count": 0, "splash_count": 0, "other_count": 0,
        "stock_sinks": 0, "customer_sinks": 0, "sink_notes_input": "",
        "load_date": datetime.date.today().strftime("%Y-%m-%d")
    }
    # Increment canvas drawing key to force signature reset
    if "canvas_key" not in st.session_state:
        st.session_state.canvas_key = "canvas_0"
    else:
        current_num = int(st.session_state.canvas_key.split("_")[1])
        st.session_state.canvas_key = f"canvas_{current_num + 1}"

# --- SIDEBAR: REFINED GROUPING BY INSTALLER COMPANY ---
st.sidebar.title("📁 Scheduled Drafts Ledger")
search_query = st.sidebar.text_input("🔍 Search Jobs / Subcontractors", "").strip().lower()

conn = get_db_connection()
saved_rows = conn.query("SELECT * FROM drafts", ttl=0)

if saved_rows is not None and not saved_rows.empty:
    grouped_by_installer = {}
    for _, row in saved_rows.iterrows():
        r_dict = dict(row)
        job_name = str(r_dict["job_number"])
        sub_co = str(r_dict["subcontractor"]) if r_dict["subcontractor"] else "Unassigned Subcontractors"
        
        if search_query in job_name.lower() or search_query in sub_co.lower():
            if sub_co not in grouped_by_installer:
                grouped_by_installer[sub_co] = []
            grouped_by_installer[sub_co].append(r_dict)
            
    if grouped_by_installer:
        for installer_co, jobs_list in grouped_by_installer.items():
            with st.sidebar.expander(f"🚛 {installer_co} ({len(jobs_list)})", expanded=True):
                sorted_jobs = sorted(jobs_list, key=lambda x: x.get("load_date", ""))
                
                for r_data in sorted_jobs:
                    date_str = str(r_data["load_date"])
                    try:
                        short_date = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d").strftime("%b %d")
                    except Exception:
                        short_date = date_str
                    
                    col_load, col_del = st.columns([4, 1])
                    
                    if col_load.button(f"📄 {r_data['job_number']} ({short_date})", key=f"load_{r_data['job_number']}", use_container_width=True):
                        st.session_state.form_buffer = r_data
                        st.rerun()
                        
                    if col_del.button("❌", key=f"del_{r_data['job_number']}"):
                        with conn.session as session:
                            session.execute(text("DELETE FROM drafts WHERE job_number = :job"), {"job": r_data['job_number']})
                            session.commit()
                        st.rerun()
            st.sidebar.markdown("---")
    else:
        st.sidebar.warning("No matching drafts found.")
else:
    st.sidebar.info("No active cloud drafts pending.")

# --- MAIN FORM INTERFACE ---
st.title("📱 Job Load-Out & Sign-Off")
st.write("Complete this form alongside the subcontractor during truck loading.")

# --- SECTION 1: JOB INFO ---
st.header("1. Job Details")
col_j1, col_j2 = st.columns([2, 1])
with col_j1:
    job_number = st.text_input("Job Name / Number", value=st.session_state.form_buffer["job_number"])
    subcontractor = st.text_input("Subcontractor Company", value=st.session_state.form_buffer["subcontractor"])
with col_j2:
    curr_dt = str(st.session_state.form_buffer.get("load_date", datetime.date.today().strftime("%Y-%m-%d")))
    try:
        parsed_dt = datetime.datetime.strptime(curr_dt[:10], "%Y-%m-%d").date()
    except Exception:
        parsed_dt = datetime.date.today()
    job_load_date = st.date_input("Scheduled Load-Out Date", value=parsed_dt)

installer_name = st.text_input("Lead Installer Name", value=st.session_state.form_buffer["installer_name"])

# --- SECTION 2: DELAYED ITEMS ---
st.header("2. Delayed Items")
default_idx = 0 if st.session_state.form_buffer["is_partial"] == "Yes - Full Job Leaving" else 1
is_partial = st.radio("Is the entire job leaving the shop today?", ["Yes - Full Job Leaving", "No - Partial Shipment"], index=default_idx)

delayed_notes = "N/A"
if is_partial == "No - Partial Shipment":
    delayed_notes = st.text_area("List rooms or pieces remaining at the shop:", value=st.session_state.form_buffer["delayed_notes"])

# --- SECTION 3: PIECE COUNTS ---
st.header("3. Physical Piece Count Loaded")
col1, col2 = st.columns(2)
with col1:
    k_count = st.number_input("Kitchen Pieces", min_value=0, step=1, value=int(st.session_state.form_buffer["k_count"]))
    mb_count = st.number_input("Primary / Master Bath Pieces", min_value=0, step=1, value=int(st.session_state.form_buffer["mb_count"]))
    ob_count = st.number_input("Additional Bath Pieces", min_value=0, step=1, value=int(st.session_state.form_buffer["ob_count"]))
with col2:
    splash_count = st.number_input("Loose Splash Pieces", min_value=0, step=1, value=int(st.session_state.form_buffer["splash_count"]))
    other_count = st.number_input("Other (Fireplace, Laundry, etc.)", min_value=0, step=1, value=int(st.session_state.form_buffer["other_count"]))

total_pieces = k_count + mb_count + ob_count + splash_count + other_count
st.metric(label="Total Pieces Checked Onto Truck", value=total_pieces)

# --- SECTION 4: SINK ACCOUNTING ---
st.header("4. Sink Accounting")
col3, col4 = st.columns(2)
with col3:
    stock_sinks = st.number_input("Shop Stock Sinks Loaded", min_value=0, step=1, value=int(st.session_state.form_buffer["stock_sinks"]))
with col4:
    customer_sinks = st.number_input("Customer-Provided Sinks Loaded", min_value=0, step=1, value=int(st.session_state.form_buffer["customer_sinks"]))

sink_notes_input = st.text_input("Sink Notes (e.g., missing sinks, specific model types, or description)", value=st.session_state.form_buffer["sink_notes_input"])
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
btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 4])

# Button 1: Save / Update Shared Cloud Draft
if btn_col1.button("💾 Save for Future Job", use_container_width=True):
    if not job_number:
        st.error("Please fill out a 'Job Name / Number' before choosing Save for Future.")
    else:
        conn = get_db_connection()
        with conn.session as session:
            session.execute(text("""
                INSERT OR REPLACE INTO drafts (
                    job_number, subcontractor, installer_name, is_partial, delayed_notes,
                    k_count, mb_count, ob_count, splash_count, other_count, stock_sinks, customer_sinks, sink_notes_input, load_date
                ) VALUES (:job_number, :subcontractor, :installer_name, :is_partial, :delayed_notes,
                          :k_count, :mb_count, :ob_count, :splash_count, :other_count, :stock_sinks, :customer_sinks, :sink_notes_input, :load_date)
            """), {
                "job_number": job_number, "subcontractor": subcontractor, "installer_name": installer_name, "is_partial": is_partial, "delayed_notes": delayed_notes,
                "k_count": k_count, "mb_count": mb_count, "ob_count": ob_count, "splash_count": splash_count, "other_count": other_count, 
                "stock_sinks": stock_sinks, "customer_sinks": customer_sinks, "sink_notes_input": sink_notes_input, "load_date": job_load_date.strftime("%Y-%m-%d")
            })
            session.commit()
        
        st.toast(f"Shared Draft {job_number} saved to Cloud!", icon="💾")
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
                    conn = get_db_connection()
                    with conn.session as session:
                        session.execute(text("DELETE FROM drafts WHERE job_number = :job"), {"job": job_number})
                        session.commit()
                    
                    st.success(f"🎉 Success! Job {job_number} load-out sheet saved.")
                    st.balloons()
                    reset_form()
                    st.rerun()
                else:
                    st.error(f"Form submission returned status code: {response.status_code}")
                    
        except Exception as e:
            st.error(f"An error occurred while saving: {e}")
