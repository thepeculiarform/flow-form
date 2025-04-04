import streamlit as st
import json
import polars as pl
import pandas as pd
import os
import time
from datetime import datetime
import platform # Keep platform import if needed elsewhere, otherwise optional
import websockets.client
import asyncio
import requests

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
            # Group changes by centerline for consolidated updates
            centerline_updates = {}
            
            for row_idx, changes in editor_state["edited_rows"].items():
                if changes and 'depth' in changes:  # Only handle depth changes
                    baffle_data = df_display.iloc[row_idx]
                    centerline_guid = baffle_data['centerline_guid']
                    
                    # Only store one update per centerline (last change wins)
                    if centerline_guid not in centerline_updates:
                        centerline_updates[centerline_guid] = {
                            'guid': centerline_guid,  # Changed from centerline_guid to guid for clarity
                            'property': 'depth',
                            'value': changes['depth']
                        }
            
            # Convert to list of edits
            current_edits = list(centerline_updates.values())
            
            if current_edits:
                st.session_state.pending_edits = current_edits
                st.warning(f"Depth changes pending for {len(current_edits)} centerline(s)")
                
                # Show what will be updated
                with st.expander("Review Changes"):
                    for edit in current_edits:
                        centerline_name = df_display[
                            df_display['centerline_guid'] == edit['guid']
                        ]['centerline_name'].iloc[0]
                        st.write(f"Centerline '{centerline_name}': Depth will be set to {edit['value']}")
                
                # Create confirmation UI
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Confirm Changes"):
                        for edit in st.session_state.pending_edits:
                            if send_edit(edit):
                                st.session_state.pending_edits.remove(edit)
                        st.session_state.confirmed_edits = True
                        st.rerun()
                with col2:
                    if st.button("Cancel Changes"):
                        st.session_state.pending_edits = []
                        st.rerun()

        # Show confirmation message if changes were just sent
        if st.session_state.confirmed_edits:
            st.success("Changes sent to Rhino!")
            st.session_state.confirmed_edits = False

    except Exception as e: st.error(f"Error displaying data editor: {e}"); print(f"Data editor error: {e}")
else: st.info(f"Waiting for data file: {DATA_FILE_OUT}")

# Manual refresh button
if st.sidebar.button("Check for Updates"): st.rerun()

# Add section to show pending edits
if st.session_state.pending_edits:
    with st.expander("Show Unsent Changes"): st.json(st.session_state.pending_edits)


refresh_rate = st.sidebar.slider("Auto-refresh rate (seconds)", 1, 30, 5)
st.sidebar.write(f"Data refreshes every {refresh_rate} seconds")

if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()

# Auto-refresh logic
if time.time() - st.session_state.last_update > refresh_rate:
    st.rerun()
    st.session_state.last_update = time.time()

class WebSocketClient:
    def __init__(self, uri="ws://localhost:8765"):
        self.uri = uri
        self.websocket = None
        
    async def connect(self):
        self.websocket = await websockets.client.connect(self.uri)
        
    async def send_edit(self, edit_data):
        if self.websocket:
            await self.websocket.send(json.dumps({
                'type': 'edit',
                'guid': edit_data['guid'],
                'property': edit_data['property'],
                'value': edit_data['value']
            }))
            
    async def receive_updates(self):
        if self.websocket:
            while True:
                message = await self.websocket.recv()
                data = json.loads(message)
                if data['type'] == 'update':
                    st.session_state.baffle_data = data['data']
                    st.rerun()

# Initialize WebSocket client
if 'ws_client' not in st.session_state:
    st.session_state.ws_client = WebSocketClient()
    asyncio.run(st.session_state.ws_client.connect())

def send_edit(edit_data):
    """Send edit to Rhino via REST API"""
    try:
        response = requests.post(
            "http://127.0.0.1:8000/edit",
            json=edit_data
        )
        if response.status_code == 200:
            st.success("Edit sent successfully")
            return True
        else:
            st.error(f"Failed to send edit: {response.json()['detail']}")
            return False
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return False