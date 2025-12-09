import streamlit as st
import pandas as pd

from backend.data_loader import load_excel
from backend.column_mapping import apply_excel_mapping, apply_sql_mapping
from backend.ws_metadata_loader import load_all_webservices, load_webservice_fields
from backend.ws_template_engine import load_template, generate_payload
from backend.ws_sender import send_payload

st.set_page_config(layout="wide", page_title="PeopleSoft → Workday Conversion Tool")

# --------------------- SESSION STATE ---------------------
if "df" not in st.session_state:
    st.session_state.df = None

if "mapped_df" not in st.session_state:
    st.session_state.mapped_df = None

if "ws_field_map" not in st.session_state:
    st.session_state.ws_field_map = {}

# --------------------- TABS ---------------------
tab1, tab2, tab3, tab4 = st.tabs(["Home", "Column Mapping", "Webservice Mapping", "Generate & Send WS"])

# =========================================================
# TAB 1: HOME
# =========================================================
with tab1:
    st.header("Step 1: Upload Legacy Excel")
    uploaded = st.file_uploader("Choose Excel File", type=["xlsx"])
    
    st.text_input("Workday Endpoint", key="endpoint")
    st.text_input("Username", key="username")
    st.text_input("Password", type="password", key="password")

    if uploaded:
        st.session_state.df = load_excel(uploaded)
        st.session_state.mapped_df = st.session_state.df.copy()
        st.success("File Loaded!")
        st.dataframe(st.session_state.mapped_df)

    if st.session_state.mapped_df is not None:
        st.download_button(
            label="Download Current Table",
            data=st.session_state.mapped_df.to_csv(index=False),
            file_name="mapped_data.csv",
            mime="text/csv"
        )

# =========================================================
# TAB 2: COLUMN MAPPING
# =========================================================
with tab2:
    st.header("Step 2: Column Mapping")

    if st.session_state.mapped_df is None:
        st.warning("⚠️ Upload a file in the Home tab first")
    else:
        df = st.session_state.mapped_df
        col = st.selectbox("Select Column to Map", df.columns)

        mapping_method = st.radio("Choose Mapping Method", ["Upload Mapping Excel", "SQL Query"])

        if mapping_method == "Upload Mapping Excel":
            map_file = st.file_uploader("Upload Mapping File", type=["xlsx"])
            if map_file and st.button("Apply Mapping"):
                st.session_state.mapped_df = apply_excel_mapping(df, col, map_file)
                st.success("Mapping Applied!")

        else:
            sql = st.text_area("Write SQL query", value=f"SELECT * FROM input_table")
            if st.button("Apply SQL"):
                st.session_state.mapped_df = apply_sql_mapping(df, sql)
                st.success("SQL Applied!")

        st.dataframe(st.session_state.mapped_df)

# =========================================================
# TAB 3: WEBSERVICE MAPPING
# =========================================================
with tab3:
    st.header("Step 3: Map Data Into Webservice Fields")

    if st.session_state.mapped_df is None:
        st.warning("Upload file first")
    else:
        ws_list = load_all_webservices()
        ws = st.selectbox("Choose Webservice", ws_list)

        fields = load_webservice_fields(ws)

        st.session_state.ws_field_map = {}

        for f in fields:
            st.session_state.ws_field_map[f] = st.selectbox(
                f"Map field '{f}' to:",
                st.session_state.mapped_df.columns
            )

        if st.button("Save Webservice Mapping"):
            st.success("Field Mapping Saved!")

# =========================================================
# TAB 4: GENERATE & SEND WS
# =========================================================
with tab4:
    st.header("Step 4: Generate Webservice Payloads and Send")

    template_file = st.selectbox(
        "Select Webservice Template",
        ["hire_worker.xml", "change_job.xml"]
    )

    template_text = load_template(f"templates/{template_file}")
    df = st.session_state.mapped_df

    st.write("### Preview First Payload")
    first_payload = generate_payload(template_text, st.session_state.ws_field_map, df.iloc[0].to_dict())
    st.code(first_payload)

    if st.button("Send All Records to Workday"):
        for _, row in df.iterrows():
            payload = generate_payload(template_text, st.session_state.ws_field_map, row.to_dict())
            code, resp = send_payload(st.session_state.endpoint, st.session_state.username, st.session_state.password, payload)
            st.write(f"Status: {code}")
            st.code(resp)

        st.success("All records processed!")
