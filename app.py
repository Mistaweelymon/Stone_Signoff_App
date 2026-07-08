import streamlit as st
from streamlit_drawable_canvas import st_canvas
import datetime
import requests
from sqlalchemy import text
import json
import base64
import io
from PIL import Image
import numpy as np
import uuid

st.set_page_config(page_title="Stone Shop Load-Out", layout="wide")

# 🔗 MAIN FORM ENDPOINT
FORM_URL = "https://docs.google.com/forms/d/1WWbNVnH7-9U3jEGjfMClNT-ZIKTXz1QZM73cCIapNJc/formResponse"

# --- SYSTEM LISTS ---
SUB_COMPANIES = ["Select Subcontractor...", "JC", "Bertin", "Eduar"]

SINK_MODELS = [
    "Select a sink...",
    "1812", "1714", "1611", 
    "Kitchen single bowl", "Kitchen 60/40", 
    "Laundry", "wet bar", 
    "Kitchen zero radius single bowl", "Laundry zero radius", "wet bar zero radius", 
    "K8206-CM1", "K8206-CM3", "K8206-CM6", 
    "K28001-CM1", "K28001-CM3", "K28001-CM6", 
    "K8223-CM1", "K8223-CM3", "K8223-CM6"
]

# --- SHARED CLOUD DATABASE CONFIGURATION ---
def get_db_connection():
    return st.connection("sqlite_project", type="sql")

def init_db():
    conn = get_db_connection()
    with conn.session as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS drafts_v2 (
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
                stock_sinks_json TEXT,
                customer_sinks INTEGER,
                sink_notes_input TEXT,
                load_date TEXT
            )
        """))
        session.commit()

init_db()

# --- HARD RESET ARCHITECTURE (FORM VERSION TRACKER) ---
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

if "form_buffer" not in st.session_state:
    st.session_state.form_buffer = {
        "job_number": "", "subcontractor": "Select Subcontractor...", "installer_name": "",
        "is_partial": "Yes - Full Job Leaving", "delayed_notes": "N/A",
        "k_count": 0, "mb_count": 0, "ob_count": 0, "splash_count": 0, "other_count": 0,
        "stock_sinks_list": [], "customer_sinks": 0, "sink_notes_input": "",
        "load_date": datetime.date.today().strftime("%Y-%m-%d")
    }

def reset_form():
    st.session_state.form_buffer = {
        "job_number": "", "subcontractor": "Select Subcontractor...", "installer_name": "",
        "is_partial": "Yes - Full Job Leaving", "delayed_notes": "N/A",
        "k_count": 0, "mb_count": 0, "ob_count": 0, "splash_count": 0, "other_count": 0,
        "stock_sinks_list": [], "customer_sinks": 0, "sink_notes_input": "",
        "load_date": datetime.date.today().strftime("%Y-%m-%d")
    }
    st.session_state.form_version += 1

# --- SIDEBAR: REFINED GROUPING BY INSTALLER COMPANY ---
st.sidebar.title("📁 Scheduled Drafts Ledger")
search_query = st.sidebar.text_input("🔍 Search Jobs / Subcontractors", "").strip().lower()

conn = get_db_connection()
saved_rows = conn.query("SELECT * FROM drafts_v2", ttl=0)

if saved_rows is not None and not saved_rows.empty:
    grouped_by_installer = {}
    for _, row in saved_rows.iterrows():
        r_dict = dict(row)
        job_name = str(r_dict["job_number"])
        sub_co = str(r_dict["subcontractor"])
        
        # Catch any blanks or defaults and group them together
        if sub_co == "Select Subcontractor..." or not sub_co:
            sub_co = "Unassigned Jobs"
            
        if search_query in job_name.lower() or search_query in sub_co.lower():
            if sub_co not in grouped_by_installer:
                grouped_by_installer[sub_co] = []
            grouped_by_installer[sub_co].append(r_dict)
            
    if grouped_by_installer:
        # Loop through the groups to create specific tabs/expanders for JC, Bertin, Eduar, etc.
        for installer_co, jobs_list in grouped_by_installer.items():
            with st.sidebar.expander(f"🚛 {installer_co} ({len(jobs_list)})", expanded=True):
                # Sort the jobs chronologically by date within this specific tab
                sorted_jobs = sorted(jobs_list, key=lambda x: x.get("load_date", ""))
                
                for r_data in sorted_jobs:
                    date_str = str(r_data["load_date"])
                    try:
                        short_date = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d").strftime("%b %d")
                    except Exception:
                        short_date = date_str
                    
                    col_load, col_del = st.columns([4, 1])
                    
                    if col_load.button(f"📄 {r_data['job_number']} ({short_date})", key=f"load_{r_data['job_number']}", use_container_width=True):
                        try:
                            loaded_sinks = json.loads(r_data["stock_sinks_json"])
                        except Exception:
                            loaded_sinks = []
                            
                        st.session_state.form_buffer = {
                            "job_number": r_data["job_number"],
                            "subcontractor": r_data["subcontractor"],
                            "installer_name": r_data["installer_name"],
                            "is_partial": r_data["is_partial"],
                            "delayed_notes": r_data["delayed_notes"],
                            "k_count": int(r_data["k_count"]),
                            "mb_count": int(r_data["mb_count"]),
                            "ob_count": int(r_data["ob_count"]),
                            "splash_count": int(r_data["splash_count"]),
                            "other_count": int(r_data["other_count"]),
                            "stock_sinks_list": loaded_sinks,
                            "customer_sinks": int(r_data["customer_sinks"]),
                            "sink_notes_input": r_data["sink_notes_input"],
                            "load_date": r_data["load_date"]
                        }
                        st.session_state.form_version += 1
                        st.rerun()
                        
                    if col_del.button("❌", key=f"del_{r_data['job_number']}"):
                        with conn.session as session:
                            session.execute(text("DELETE FROM drafts_v2 WHERE job_number = :job"), {"job": r_data['job_number']})
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

v = st.session_state.form_version

# --- SECTION 1: JOB INFO ---
st.header("1. Job Details")
col_j1, col_j2 = st.columns([2, 1])
with col_j1:
    job_number = st.text_input("Job Name / Number", value=st.session_state.form_buffer["job_number"], key=f"job_num_{v}")
    
    # Check buffer for dropdown index
    curr_sub = st.session_state.form_buffer["subcontractor"]
    sub_idx = SUB_COMPANIES.index(curr_sub) if curr_sub in SUB_COMPANIES else 0
    subcontractor = st.selectbox("Subcontractor Company", SUB_COMPANIES, index=sub_idx, key=f"sub_{v}")
    
with col_j2:
    curr_dt = str(st.session_state.form_buffer.get("load_date", datetime.date.today().strftime("%Y-%m-%d")))
    try:
        parsed_dt = datetime.datetime.strptime(curr_dt[:10], "%Y-%m-%d").date()
    except Exception:
        parsed_dt = datetime.date.today()
    job_load_date = st.date_input("Scheduled Load-Out Date", value=parsed_dt, key=f"date_{v}")

installer_name = st.text_input("Lead Installer Name", value=st.session_state.form_buffer["installer_name"], key=f"inst_name_{v}")

# --- SECTION 2: DELAYED ITEMS ---
st.header("2. Delayed Items")
default_idx = 0 if st.session_state.form_buffer["is_partial"] == "Yes - Full Job Leaving" else 1
is_partial = st.radio("Is the entire job leaving the shop today?", ["Yes - Full Job Leaving", "No - Partial Shipment"], index=default_idx, key=f"partial_{v}")

delayed_notes = "N/A"
if is_partial == "No - Partial Shipment":
    delayed_notes = st.text_area("List rooms or pieces remaining at the shop:", value=st.session_state.form_buffer["delayed_notes"], key=f"delayed_{v}")

# --- SECTION 3: PIECE COUNTS ---
st.header("3. Physical Piece Count Loaded")
col1, col2 = st.columns(2)
with col1:
    k_count = st.number_input("Kitchen Pieces", min_value=0, step=1, value=int(st.session_state.form_buffer["k_count"]), key=f"k_{v}")
    mb_count = st.number_input("Primary / Master Bath Pieces", min_value=0, step=1, value=int(st.session_state.form_buffer["mb_count"]), key=f"mb_{v}")
    ob_count = st.number_input("Additional Bath Pieces", min_value=0, step=1, value=int(st.session_state.form_buffer["ob_count"]), key=f"ob_{v}")
with col2:
    splash_count = st.number_input("Loose Splash Pieces", min_value=0, step=1, value=int(st.session_state.form_buffer["splash_count"]), key=f"splash_{v}")
    other_count = st.number_input("Other (Fireplace, Laundry, etc.)", min_value=0, step=1, value=int(st.session_state.form_buffer["other_count"]), key=f"other_{v}")

total_pieces = k_count + mb_count + ob_count + splash_count + other_count
st.metric(label="Total Pieces Checked Onto Truck", value=total_pieces)

# --- SECTION 4: SINK ACCOUNTING ---
st.header("4. Sink Accounting")

# Dynamic Stock Sinks UI
st.subheader("🛒 Shop Stock Sinks")
for sink in st.session_state.form_buffer["stock_sinks_list"]:
    sc1, sc2, sc3 = st.columns([6, 2, 1])
    with sc1:
        current_idx = SINK_MODELS.index(sink["model"]) if sink["model"] in SINK_MODELS else 0
        sink["model"] = st.selectbox("Model", SINK_MODELS, index=current_idx, key=f"mod_{sink['id']}_{v}", label_visibility="collapsed")
    with sc2:
        sink["qty"] = st.number_input("Qty", min_value=1, step=1, value=sink["qty"], key=f"qty_{sink['id']}_{v}", label_visibility="collapsed")
    with sc3:
        if st.button("❌", key=f"del_{sink['id']}_{v}"):
            st.session_state.form_buffer["stock_sinks_list"].remove(sink)
            st.rerun()

if st.button("➕ Add Stock Sink"):
    st.session_state.form_buffer["stock_sinks_list"].append({"id": str(uuid.uuid4()), "model": SINK_MODELS[0], "qty": 1})
    st.rerun()

st.markdown("---")

col_cust1, col_cust2 = st.columns(2)
with col_cust1:
    customer_sinks = st.number_input("Customer-Provided Sinks Loaded", min_value=0, step=1, value=int(st.session_state.form_buffer["customer_sinks"]), key=f"csink_{v}")
with col_cust2:
    sink_notes_input = st.text_input("Sink Notes (Missing sinks, descriptions, etc.)", value=st.session_state.form_buffer["sink_notes_input"], key=f"snote_{v}")

# Process the dynamic sink list into a clean string for Google Sheets
sink_notes_final = "None" if not sink_notes_input else sink_notes_input
stock_sinks_formatted = ", ".join([f"{s['qty']}x {s['model']}" for s in st.session_state.form_buffer["stock_sinks_list"] if s['model'] != "Select a sink..."])
if not stock_sinks_formatted:
    stock_sinks_formatted = "None"

sinks_notes = f"Stock Sinks: [{stock_sinks_formatted}] | Customer Sinks: {customer_sinks} | Sink Notes: {sink_notes_final}"

# --- SECTION 5: SIGNATURE ---
st.header("5. Custody Transfer & Sign-Off")
st.warning("Installer Acknowledgment: By signing below, I confirm that I have physically counted and inspected the loaded items.")

st.write("Lead Installer Signature:")
canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.3)", stroke_width=3, stroke_color="#000000",
    background_color="#ffffff", height=150, drawing_mode="freedraw", key=f"canvas_{v}",
)

# --- ACTION FOOTER BUTTONS ---
st.markdown("---")
btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 4])

if btn_col1.button("💾 Save for Future Job", use_container_width=True):
    if not job_number or subcontractor == "Select Subcontractor...":
        st.error("Please fill out a 'Job Name / Number' and select a 'Subcontractor' before choosing Save for Future.")
    else:
        conn = get_db_connection()
        with conn.session as session:
            session.execute(text("""
                INSERT OR REPLACE INTO drafts_v2 (
                    job_number, subcontractor, installer_name, is_partial, delayed_notes,
                    k_count, mb_count, ob_count, splash_count, other_count, stock_sinks_json, customer_sinks, sink_notes_input, load_date
                ) VALUES (:job_number, :subcontractor, :installer_name, :is_partial, :delayed_notes,
                          :k_count, :mb_count, :ob_count, :splash_count, :other_count, :stock_sinks_json, :customer_sinks, :sink_notes_input, :load_date)
            """), {
                "job_number": job_number, "subcontractor": subcontractor, "installer_name": installer_name, "is_partial": is_partial, "delayed_notes": delayed_notes,
                "k_count": k_count, "mb_count": mb_count, "ob_count": ob_count, "splash_count": splash_count, "other_count": other_count, 
                "stock_sinks_json": json.dumps(st.session_state.form_buffer["stock_sinks_list"]), 
                "customer_sinks": customer_sinks, "sink_notes_input": sink_notes_input, "load_date": job_load_date.strftime("%Y-%m-%d")
            })
            session.commit()
        st.toast(f"Shared Draft {job_number} saved to Cloud!", icon="💾")
        reset_form()
        st.rerun()

if btn_col2.button("🧹 Clear Form Screen", use_container_width=True):
    reset_form()
    st.rerun()

if btn_col3.button("Submit Load-Out Sheet", type="primary", use_container_width=True):
    if not job_number or not installer_name or subcontractor == "Select Subcontractor...":
        st.error("Please fill out the Job Number, Subcontractor, and Installer Name before submitting.")
    elif not canvas_result.json_data or len(canvas_result.json_data["objects"]) == 0:
        st.error("The Lead Installer must sign the signature box before submitting.")
    else:
        with st.spinner("Processing signature and saving data..."):
            try:
                IMGBB_KEY = st.secrets["IMGBB_API"]
            except KeyError:
                st.error("🚨 Missing 'IMGBB_API' key! Please check your Streamlit Secrets panel.")
                st.stop()
                
            try:
                # --- IMAGE PROCESSING ---
                img_array = canvas_result.image_data
                img = Image.fromarray(img_array.astype('uint8'), 'RGBA')
                background = Image.new("RGBA", img.size, (255, 255, 255, 255))
                composite = Image.alpha_composite(background, img).convert("RGB")
                
                buffer = io.BytesIO()
                composite.save(buffer, format="PNG")
                img_b64 = base64.b64encode(buffer.getvalue()).decode()
                
                # --- IMAGE UPLOAD ---
                upload_response = requests.post(f"https://api.imgbb.com/1/upload?key={IMGBB_KEY}", data={"image": img_b64})
                if upload_response.status_code == 200:
                    signature_link = upload_response.json()["data"]["url"]
                else:
                    st.error(f"🚨 ImgBB Upload Failed: Server responded with code {upload_response.status_code}. {upload_response.text}")
                    st.stop()
                    
                # --- GOOGLE FORM SUBMISSION ---
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                text_summary = (
                    f"Job: {job_number} | Co: {subcontractor} | Name: {installer_name} | Total Loaded: {total_pieces} | "
                    f"Breakdown: [K:{k_count}, MB:{mb_count}, Bath:{ob_count}, Splash:{splash_count}, Other:{other_count}] | "
                    f"Sinks: {sinks_notes} | Delayed: {delayed_notes}"
                )
                
                # Form Payload
                form_data = {"entry.2095053729": text_summary, "entry.2107411274": signature_link}
                headers = {
                    "Referer": FORM_URL.replace("/formResponse", "/viewform"),
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                response = requests.post(FORM_URL, data=form_data, headers=headers)
                
                if response.status_code == 200:
                    conn = get_db_connection()
                    with conn.session as session:
                        session.execute(text("DELETE FROM drafts_v2 WHERE job_number = :job"), {"job": job_number})
                        session.commit()
                    
                    st.success(f"🎉 Success! Job {job_number} load-out sheet saved.")
                    st.balloons()
                    reset_form()
                    st.rerun()
                else:
                    st.error(f"Form submission returned status code: {response.status_code}")
                    
            except Exception as e:
                st.error(f"An error occurred while saving: {e}")
