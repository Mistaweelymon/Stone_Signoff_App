import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_drawable_canvas import st_canvas
import datetime
import pandas as pd
import json

st.set_page_config(page_title="Stone Shop Load-Out", layout="centered")

st.title("📱 Job Load-Out & Sign-Off")
st.write("Complete this form alongside the subcontractor during truck loading.")

# Connect to Google Sheets using the secrets.toml configuration
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1: JOB INFO ---
st.header("1. Job Details")
job_number = st.text_input("Job Name / Number")
subcontractor = st.text_input("Subcontractor Company")
installer_name = st.text_input("Lead Installer Name")

# --- SECTION 2: DELAYED ITEMS ---
st.header("2. Delayed Items")
is_partial = st.radio("Is the entire job leaving the shop today?", ["Yes - Full Job Leaving", "No - Partial Shipment"])
delayed_notes = ""
if is_partial == "No - Partial Shipment":
    delayed_notes = st.text_area("List rooms or pieces remaining at the shop (e.g., 'Master Bath delayed'):")

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

# --- SECTION 4: SINKS & ACCESSORIES ---
st.header("4. Sinks, Hardware & Extras")
sinks_hardware = st.multiselect(
    "Select all items physically verified and loaded:",
    ["Under-mount Sinks", "Vessel / Drop-in Sinks", "Sink Templates", "Mounting Hardware / Clips", "Faucets / Accessories"]
)
sinks_notes = ", ".join(sinks_hardware)

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
            with st.spinner("Saving to Google Sheets..."):
                # 1. Pull existing rows down
                existing_data = conn.read()
                
                # 2. Format new row data
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sig_data = json.dumps(canvas_result.json_data["objects"])
                
                new_row = pd.DataFrame([{
                    "Timestamp": timestamp,
                    "Job Number": job_number,
                    "Installer Company": subcontractor,
                    "Installer Name": installer_name,
                    "Kitchen Count": k_count,
                    "Master Bath Count": mb_count,
                    "Other Baths Count": ob_count,
                    "Splash Count": splash_count,
                    "Other Count": other_count,
                    "Total Loaded": total_pieces,
                    "Sinks Hardware": sinks_notes,
                    "Delayed Items": delayed_notes if delayed_notes else "N/A",
                    "Signature Data": sig_data
                }])
                
                # 3. Add new row to existing data and send back to Google Sheets
                updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                conn.update(data=updated_df)
                
                st.success(f"🎉 Success! Job {job_number} sign-off sheet saved to Google Sheets.")
                st.balloons()
        except Exception as e:
            st.error(f"An error occurred while saving: {e}")