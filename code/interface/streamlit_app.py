import streamlit as st
import time
import json
from pathlib import Path

def load_rhino_data(filepath):
    """Load data from a JSON file that Rhino updates"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def main():
    # Setup persistent state
    if 'last_modified' not in st.session_state:
        st.session_state.last_modified = 0

    # Static header
    with st.container():
        st.title('Rhino Live Data Viewer')
        st.write('Monitoring data updates from Rhino...')

    # Create placeholders for dynamic content
    data_display = st.empty()
    status_display = st.empty()

    # Data file path - adjust this to match where Rhino writes the data
    data_file = Path("rhino_data.json")

    while True:
        try:
            # Check if file exists and has been modified
            current_modified = data_file.stat().st_mtime if data_file.exists() else 0
            
            if current_modified > st.session_state.last_modified:
                # Load and display new data
                data = load_rhino_data(data_file)
                with data_display:
                    st.json(data)
                with status_display:
                    st.success(f"Last updated: {time.strftime('%H:%M:%S')}")
                st.session_state.last_modified = current_modified
            
            time.sleep(0.1)  # Small delay to prevent excessive CPU usage
            
        except Exception as e:
            with status_display:
                st.error(f"Error: {e}")
            time.sleep(1)

if __name__ == '__main__':
    main()

