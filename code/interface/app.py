import streamlit as st
import json
import polars as pl
import pandas as pd
import os
from datetime import datetime
import requests

# --- Configuration ---
# Use absolute paths for reliability
project_root = r"e:/Projects/tpf/rhino/flow_form" # Use raw string for Windows paths
DATA_FILE_OUT = os.path.join(project_root, "code", "data", "baffle_data_out.json") # Data coming from Grasshopper
EDITS_FILE_IN = os.path.join(project_root, "code", "data", "baffle_edits_in.json") # Edits going to Grasshopper
API_URL = "http://127.0.0.1:8001"


# --- File Handling ---
def read_data_file(filepath):
    """Reads the JSON data file from Grasshopper."""
    try:
        if os.path.exists(filepath):
            mod_time = os.path.getmtime(filepath)
            with open(filepath, 'r') as f:
                content = f.read()
                if not content.strip():
                    print(f"Data file is empty: {filepath}")
                    return None, mod_time
                data = json.loads(content)
            return data, mod_time
        else:
            return None, 0
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {filepath}. File might be empty or corrupted.")
        try: mod_time = os.path.getmtime(filepath)
        except OSError: mod_time = st.session_state.get('last_read_time', 0)
        return None, mod_time
    except Exception as e:
        print(f"Error reading data file {filepath}: {e}")
        return None, st.session_state.get('last_read_time', 0)


def write_edits_file(filepath, edits):
    """Writes the edits from Streamlit to a JSON file for Grasshopper."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        print(f"Writing edits to {filepath}:")
        print(json.dumps(edits, indent=2))  # Debug: Show what we're writing
        with open(filepath, 'w') as f:
            json.dump(edits, f, indent=4)
        print(f"Edits successfully written to {filepath}")
        st.session_state.pending_edits = []  # Clear pending edits
        st.toast(f"{len(edits)} edits sent to Grasshopper")
        return True
    except Exception as e:
        print(f"Error writing edits file {filepath}: {e}")
        st.error(f"Failed to send edits: {e}")
        return False


def on_property_change():
    """Handle property changes with confirmation"""
    if st.session_state.pending_changes:
        with st.form(key='confirm_changes'):
            st.write("Pending Changes:")
            for change in st.session_state.pending_changes:
                st.write(f"- {change['object']}: {change['property']} = {change['value']}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Confirm Changes"):
                    write_edits_file(EDITS_FILE_IN, st.session_state.pending_changes)
                    st.session_state.pending_changes = []
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.pending_changes = []





def fetch_baffle_data():
    """Fetch baffle data from FastAPI"""
    try:
        response = requests.get(f"{API_URL}/baffles")
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        else:
            st.error(f"Failed to fetch data: {response.text}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return pd.DataFrame()


def send_edit(edit):
    """Send edit to FastAPI"""
    try:
        response = requests.post(
            f"{API_URL}/edit",
            json=edit
        )
        if response.status_code == 200:
            st.success("Edit sent successfully")
            return True
        else:
            # Handle non-200 responses
            try:
                error_detail = response.json().get('detail', 'Unknown error')
            except Exception:
                error_detail = response.text
            st.error(f"Failed to send edit: {error_detail}")
            return False
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return False
    

# --- Streamlit UI ---

st.set_page_config(
    layout="wide",
    page_title="Baffle Controller",
    page_icon="🔄"
)


# Initialize session state variables
if 'baffle_data' not in st.session_state: st.session_state.baffle_data = pl.DataFrame()
if 'last_read_time' not in st.session_state: st.session_state.last_read_time = 0
if 'pending_edits' not in st.session_state: st.session_state.pending_edits = []
if 'confirmed_edits' not in st.session_state: st.session_state.confirmed_edits = False

# --- Data Loading based on File Modification Time ---
raw_data, current_mod_time = read_data_file(DATA_FILE_OUT)

if current_mod_time > st.session_state.last_read_time:
    print("Data file has changed, reloading...")
    data_changed_flag = False
    new_df = None
    if raw_data is not None:
        try:
            if isinstance(raw_data, list) and not raw_data: new_df = pl.DataFrame()
            else: new_df = pl.DataFrame(raw_data)
        except Exception as e:
            st.error(f"Error processing data from file: {e}"); print(f"Error processing data from file: {e}")
            new_df = pl.DataFrame() # Clear data on error
    else: new_df = pl.DataFrame() # Clear data if file empty/error

    # Update state if new_df was successfully created (is not None)
    if new_df is not None:
        # Always update the state if we successfully parsed a new DataFrame
        # (even if it's empty, reflecting the latest state from the file)
        st.session_state.baffle_data = new_df
        print("Updated st.session_state.baffle_data from file")
        data_changed_flag = True
    # else: new_df is None (due to read error) - state already cleared before this block

    st.session_state.last_read_time = current_mod_time # Update time regardless
    if data_changed_flag: st.rerun() # Rerun only if data changed

# Display last update time
if st.session_state.last_read_time > 0:
     last_update_dt = datetime.fromtimestamp(st.session_state.last_read_time)
     st.sidebar.write(f"Data last checked: {last_update_dt.strftime('%Y-%m-%d %H:%M:%S')}")
else: st.sidebar.write("Status: Waiting for data file...")


## -- UI Elements -- ##

#######################
# CSS styling
st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 15px 0;
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}

[data-testid="stMetricDeltaIcon-Up"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

[data-testid="stMetricDeltaIcon-Down"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

</style>
""", unsafe_allow_html=True)

# Display and Edit Data
st.header("Baffle Data")

if not st.session_state.baffle_data.is_empty():
    try:
        st.write("Hello")
        # Two equal columns:
        col1, col2 = st.columns(2)
        col1.write("This is column 1")
        col2.write("This is column 2")
        # Debug: Show the raw baffle data
        st.write("Baffle Data (Polars):", st.session_state.baffle_data)

        # Group by 'centerline_guid' and select the first row for each unique centerline
        unique_centerlines = (
            st.session_state.baffle_data
            .group_by("centerline_guid")
            .agg(pl.col("centerline_name").first(), pl.col("depth").first())
            .sort("centerline_name")
        )

        # Debug: Show the unique centerlines
        st.write("Unique Centerlines (Polars):", unique_centerlines)

        # Iterate over unique centerlines
        for centerline in unique_centerlines.to_dicts():
            # Ensure required keys exist
            if 'centerline_name' not in centerline or 'centerline_guid' not in centerline or 'depth' not in centerline:
                st.warning("Missing required keys in centerline data")

            # Ensure depth is a valid number
            try:
                depth_value = float(centerline['depth'])
            except (ValueError, TypeError):
                st.warning(f"Invalid depth value for centerline: {centerline}")
                continue

            # Display the centerline in an expander
            with st.expander(f"Centerline: {centerline['centerline_name']}"):
                new_depth = st.slider(
                    "Depth",
                    min_value=0.0,
                    max_value=2.0,
                    value=depth_value,
                    key=f"depth_{centerline['centerline_guid']}"
                )

                # If the depth is changed, send an edit
                if new_depth != depth_value:
                    edit = {
                        "guid": centerline['centerline_guid'],
                        "property": "depth",
                        "value": new_depth
                    }
                    if send_edit(edit):
                        st.rerun()

    except Exception as e:
        st.error(f"Error displaying data editor: {e}")
        print(f"Data editor error: {e}")
else:
    st.info("No baffle data available. Please check the data file or API.")

# Manual refresh button
if st.sidebar.button("Check for Updates"): st.rerun()

# # Add section to show pending edits
# if st.session_state.pending_edits:
#     with st.expander("Show Unsent Changes"): st.json(st.session_state.pending_edits)
