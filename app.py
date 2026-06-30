import streamlit as st
from streamlit_drawable_canvas import st_canvas
import datetime
import requests
import json

st.set_page_config(page_title="Stone Shop Load-Out", layout="centered")

st.title("📱 Job Load-Out & Sign-Off")
st.write("Complete this form alongside the subcontractor during truck loading.")

# Hardcoded direct public form gateway link
FORM_URL = "https://docs.google.com/forms/d/1WWbNVnH7-9U3jEGjfMClNT-ZIKTXz1QZM73cCIapNJc/formResponse"

# --- SECTION 1: JOB INFO ---
st.header("1. Job Details")
job_number = st.text_input("Job Name / Number")
subcontractor = st.text_input("Subcontractor Company")
installer_name = st.text_input("Lead Installer Name")

# --- SECTION 2: DELAYED ITEMS ---
st.header("2. Delayed Items")
is_partial = st.radio("Is the entire job leaving the shop today?", ["Yes - Full Job Leaving", "No - Partial Shipment"])
delayed_notes = "N/A"
if is_partial == "No - Partial Shipment":
    delayed_notes = st.text_area("List rooms or pieces remaining at the shop:")

# --- SECTION 3: PIECE COUNTS ---
st.header("3. Physical Piece Count Loaded")
col1, col2 = st.columns(2)
with col1:
    k_count = st.number_input("Kitchen Pieces", min_value=0, step=1)
    mb_count = st.number_input("Primary / Master Bath Pieces", min_value=0, step=1)
    ob_count = st.number_input("Additional Bath Pieces", min_value=0, step=1)
with col2:
    splash_count = st.number_input("Loose Splash Pieces", min_value=0, step=1)
    other_count = st.number_input("Other (Fireplace, Laundry, etc.)", min_value=0, step=1)

total_pieces = k_count + mb_count + ob_count + splash_count + other_count
st.metric(label="Total Pieces Checked Onto Truck", value=total_pieces)

# --- SECTION 4: SINK VERIFICATION & DISPUTE PROTECTION ---
st.header("4. Sink Accounting")
st.write("Log exactly who provided the sinks to prevent field disputes:")

col3, col4 = st.columns(2)
with col3:
    stock_sinks = st.number_input("Shop Stock Sinks Loaded", min_value=0, step=1)
with col4:
    customer_sinks = st.number_input("Customer-Provided Sinks Loaded", min_value=0, step=1)

# Replaced the multiselect checklist with a clean, open text box for sink details
sink_notes_input = st.text_input("Sink Notes (e.g., missing sinks, specific model types, or description)")
if not sink_notes_input:
    sink_notes_input = "None"

# Compile a clean, descriptive sink ledger string
sinks_notes = f"Stock Sinks: {stock_sinks} | Customer Sinks: {customer_sinks} | Sink Notes: {sink_notes_input}"

# --- SECTION 5: SIGNATURE ---
st.header("5. Custody Transfer & Sign-Off")
st.warning(
    "Installer Acknowledgment: By signing below, I confirm that I have physically counted and inspected the loaded items. "
    "I verify that any delayed areas are explicitly left behind, and everything else is present and loaded in good condition."
)

st.write("Lead Installer Signature:")
canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.3)",
    stroke_width=3,
    stroke_color="#000000",
    background_color="#eee",
    height=150,
    drawing_mode="freedraw",
    key="canvas",
)

# --- SUBMIT BUTTON ---
if st.button("Submit Load-Out Sheet", type="primary"):
    if not job_number or not installer_name or not subcontractor:
        st.error("Please fill out the Job Number, Subcontractor, and Installer Name before submitting.")
    elif not canvas_result.json_data or len(canvas_result.json_data["objects"]) == 0:
        st.error("The Lead Installer must sign the signature box before submitting.")
    else:
        try:
            with st.spinner("Saving data securely..."):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sig_data = json.dumps(canvas_result.json_data["objects"])
                
                # Sinks notes are seamlessly packaged into the text string
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
                    st.success(f"🎉 Success! Job {job_number} load-out sheet saved.")
                    st.balloons()
                else:
                    st.error(f"Form submission returned status code: {response.status_code}")
                    
        except Exception as e:
            st.error(f"An error occurred while saving: {e}")
