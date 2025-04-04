import streamlit as st
import json
import polars as pl
import pandas as pd
import os
import time
from datetime import datetime
import platform # Keep platform import if needed elsewhere, otherwise optional

# --- Configuration ---
# Use absolute paths for reliability
project_root = r"e:/Projects/tpf/rhino/flow_form" # Use raw string for Windows paths
DATA_FILE_OUT = os.path.join(project_root, "code", "data", "baffle_data_out.json") # Data coming from Grasshopper
EDITS_FILE_IN = os.path.join(project_root, "code", "data", "baffle_edits_in.json") # Edits going to Grasshopper

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
        with open(filepath, 'w') as f:
            json.dump(edits, f, indent=4)
        print(f"Edits successfully written to {filepath}")
        st.session_state.pending_edits = [] # Clear pending edits
        st.toast(f"{len(edits)} edits sent to Grasshopper.")
    except Exception as e:
        print(f"Error writing edits file {filepath}: {e}")
        st.error(f"Failed to send edits: {e}")


# --- Streamlit UI ---

st.set_page_config(layout="wide")
st.title("Rhino/Grasshopper Baffle Controller")

# Initialize session state variables
if 'baffle_data' not in st.session_state: st.session_state.baffle_data = pl.DataFrame()
if 'last_read_time' not in st.session_state: st.session_state.last_read_time = 0
if 'pending_edits' not in st.session_state: st.session_state.pending_edits = []

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


# Display and Edit Data
st.header("Baffle Data")

if not st.session_state.baffle_data.is_empty():
    try:
        df_display = st.session_state.baffle_data.to_pandas()
        column_config = {
            "baffle_id": st.column_config.TextColumn("Baffle ID", disabled=True),
            "centerline_guid": st.column_config.TextColumn("Centerline GUID", disabled=True),
            "centerline_name": st.column_config.TextColumn("Centerline Name", disabled=True),
            "length": st.column_config.NumberColumn("Length", format="%.2f", disabled=True),
            "depth": st.column_config.NumberColumn("Depth", format="%.2f", disabled=False),
            "type": st.column_config.TextColumn("Curve Type", disabled=True),
        }
        edited_df_pandas = st.data_editor(
            df_display, column_config=column_config, use_container_width=True,
            num_rows="fixed", key="baffle_editor"
        )

        # --- Detect and Queue Changes ---
        editor_state = st.session_state.baffle_editor
        if editor_state.get("edited_rows"):
            current_edits = editor_state["edited_rows"]
            for row_idx, changes in current_edits.items():
                 if changes:
                    centerline_guid = df_display.iloc[row_idx]['centerline_guid']
                    edit_payload = {'centerline_guid': centerline_guid, 'update': changes, 'timestamp': time.time()}
                    is_duplicate = False
                    for i, existing_edit in enumerate(st.session_state.pending_edits):
                        if (existing_edit.get('centerline_guid') == edit_payload['centerline_guid']):
                            st.session_state.pending_edits[i] = edit_payload; is_duplicate = True; break
                    if not is_duplicate: st.session_state.pending_edits.append(edit_payload)
                    print(f"Queued edit: {edit_payload}")

        # --- Button to Apply Changes ---
        if st.session_state.pending_edits:
            st.warning(f"{len(st.session_state.pending_edits)} unsent changes.")
            if st.button("Apply Changes to Rhino Properties"):
                write_edits_file(EDITS_FILE_IN, st.session_state.pending_edits)
                # Rerun to clear warning/button state after sending
                st.rerun()

    except Exception as e: st.error(f"Error displaying data editor: {e}"); print(f"Data editor error: {e}")
else: st.info(f"Waiting for data file: {DATA_FILE_OUT}")

# Manual refresh button
if st.sidebar.button("Check for Updates"): st.rerun()

# Add section to show pending edits
if st.session_state.pending_edits:
    with st.expander("Show Unsent Changes"): st.json(st.session_state.pending_edits)
