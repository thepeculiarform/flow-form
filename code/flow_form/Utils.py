import Rhino as rh
import Rhino.Geometry as rg
import scriptcontext as sc
import subprocess
import psutil
import os
import System
import time
import polars as pl


import flow_form as pjct

# Set Rhino document context at module level
sc.doc = rh.RhinoDoc.ActiveDoc


alpha = "abcdefghijklmnopqrstuvwxyz"


import json
def save_to_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def delete_group_items(name):
    a_group = sc.doc.Groups.FindName(name)
    if not a_group:
        pass
    else:
        group_items = sc.doc.Objects.FindByGroup(a_group.Index)
        if len(group_items) > 0:
            for item in group_items:
                sc.doc.Objects.Delete(item)


def kill_streamlit_process(pid=None):
    """Force kills Streamlit process and child processes"""
    try:
        if pid and psutil.pid_exists(pid):
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                child.kill()
            parent.kill()
            return True
        return False
    except:
        return False


def kill_fastapi_process(pid=None):
    """Force kills FastAPI/uvicorn process and child processes"""
    try:
        if pid and psutil.pid_exists(pid):
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                child.kill()
            parent.kill()
            return True
        return False
    except:
        return False


def manage_streamlit_server(action="start", port=8501):
    """Manages the Streamlit server process"""
    # Get project root from current file location
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    # Build paths relative to project root
    streamlit_script = os.path.join(project_root, "code", "interface", "app.py")
    pid_file = os.path.join(project_root, "code", "interface", "streamlit.pid")
    
    
    if action == "start":
        print("Attempting to start Streamlit server...")
        print(f"Script path: {streamlit_script}")
        print(f"PID file: {pid_file}")

        # Ensure script exists
        if not os.path.exists(streamlit_script):
            print(f"Error: Streamlit script not found at {streamlit_script}")
            return False

        # Check if already running using PID file
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                try:
                    pid = int(f.read().strip())
                    if psutil.pid_exists(pid):
                        print(f"Streamlit server already running (PID: {pid})")
                        return True
                except:
                    pass
            print("Removing stale PID file")
            os.remove(pid_file)

        # Start new process
        try:
            # Use streamlit directly instead of python -m
            cmd = ["streamlit", "run", streamlit_script, 
                  "--server.port", str(port)]
            
            print(f"Launching command: {' '.join(cmd)}")
            
            # Don't capture output to allow console window to show it
            process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=None,  # Changed from PIPE to None
                stderr=None,  # Changed from PIPE to None
                shell=True    # Changed to True for Windows
            )
            
            # Brief pause to let process start
            import time
            time.sleep(1)
            
            if process.poll() is not None:
                print("Error: Process terminated immediately")
                return False
                
            # Save PID to file
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
                
            print(f"Started Streamlit server on port {port} (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"Error starting Streamlit: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    elif action == "stop":
        stopped = False
        # Try to stop using PID file first
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                try:
                    pid = int(f.read().strip())
                    stopped = kill_streamlit_process(pid)
                except:
                    pass
            os.remove(pid_file)
            
        # Fallback: stop all Streamlit processes
        if not stopped:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'streamlit' in str(proc.info.get('cmdline', '')):
                    try:
                        kill_streamlit_process(proc.info['pid'])
                        stopped = True
                    except:
                        pass
                        
        print("Stopped Streamlit server" if stopped else "No server running")
        return stopped


def manage_fastapi_server(action="start", port=8000):
    """Manages the FastAPI server process"""
    # Get Rhino Python executable dynamically
    rhino_python = get_rhino_python_path()
    if not rhino_python:
        print("Error: Could not determine Rhino Python path. Aborting FastAPI server management.")
        return False
    
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    interface_dir = os.path.join(project_root, "code", "interface")
    api_script = os.path.join(interface_dir, "api_app.py")
    pid_file = os.path.join(interface_dir, "fastapi.pid")

    if action == "start":
        print("Attempting to start FastAPI server...")
        print(f"Using Python: {rhino_python}")
        print(f"Script path: {api_script}")
        print(f"PID file: {pid_file}")

        # Check if already running
        # ...existing code for PID check...

        try:
            cmd = [rhino_python, "-m", "uvicorn", "api_app:app", 
                  "--host", "127.0.0.1", "--port", str(port)]
            
            print(f"Launching command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=None,
                stderr=None,
                shell=True,
                cwd=interface_dir
            )
            
            time.sleep(1)
            
            if process.poll() is not None:
                print("Error: Process terminated immediately")
                return False
                
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
                
            print(f"Started FastAPI server on port {port} (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"Error starting FastAPI: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    elif action == "stop":
        stopped = False
        # Try to stop using PID file first
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                try:
                    pid = int(f.read().strip())
                    stopped = kill_fastapi_process(pid)
                except:
                    pass
            os.remove(pid_file)
            
        # Fallback: stop all uvicorn processes
        if not stopped:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = str(proc.info.get('cmdline', ''))
                if 'uvicorn' in cmdline and 'api_app:app' in cmdline:
                    try:
                        kill_fastapi_process(proc.info['pid'])
                        stopped = True
                    except:
                        pass
                        
        print("Stopped FastAPI server" if stopped else "No server running")
        return stopped


def update_object_usertext(obj_id, property_name, value):
    """Updates UserText on Rhino object and triggers update"""
    try:
        obj = sc.doc.Objects.Find(obj_id)
        if obj:
            obj.Attributes.SetUserString(property_name, str(value))
            obj.CommitChanges()
            sc.doc.Views.Redraw()
            return True
        return False
    except Exception as e:
        print(f"Error updating UserText: {e}")
        return False

def process_baffle_edits():
    """Process edits from Streamlit and update the 'depth' UserText field of Rhino objects"""
    edits_file = get_data_path("baffle_edits_in.json")  # Use consistent path resolution
    if os.path.exists(edits_file):
        try:
            # Read edits from the JSON file
            with open(edits_file, 'r') as f:
                edits = json.load(f)
            
            # Apply each edit
            for edit in edits:
                guid = System.Guid.Parse(edit['guid'])  # Parse the GUID
                obj = sc.doc.Objects.Find(guid)  # Find the Rhino object by GUID
                if obj:
                    # Update the 'depth' field in UserText
                    if edit['property'] == 'depth':
                        obj.Attributes.SetUserString('depth', str(edit['value']))
                        obj.CommitChanges()  # Commit changes to the Rhino document
                        print(f"Updated depth for object {guid} to {edit['value']}")
            
            # Remove the edits file after processing
            os.remove(edits_file)
            return True
        except Exception as e:
            print(f"Error processing edits: {e}")
            return False
    return False


def get_baffle_data(centerline_layer, default_depth=1000.0):
    """Collects current baffle data from BaffleCenterline objects and writes it as a Polars DataFrame to JSON"""
    data_path = get_data_path("baffle_data.json")
    print(f"Data path resolved to: {data_path}")  # Debug print

    try:
        # Get the centerline layer
        layer_index = sc.doc.Layers.Find(centerline_layer, True)
        if layer_index == -1:
            print(f"Error: Layer '{centerline_layer}' not found.")
            return pl.DataFrame()

        # Get all objects on the centerline layer
        layer_objects = sc.doc.Objects.FindByLayer(sc.doc.Layers[layer_index])
        baffle_data_list = []

        # Process each centerline object
        for i, obj in enumerate(layer_objects):
            if isinstance(obj.Geometry, rg.Curve):  # Ensure the object is a curve
                # Create a BaffleCenterline instance
                centerline_name = f"BaffleCenterline_{i + 1}"
                depth = obj.Attributes.GetUserString("depth")
                depth = float(depth) if depth else default_depth

                baffle_centerline = pjct.Project.BaffleCenterline(
                    name=centerline_name,
                    centerline=obj,
                    depth=depth
                )

                # Process each Baffle associated with the BaffleCenterline
                for baffle in baffle_centerline.baffles:
                    baffle_data_list.append({
                        "length": round(baffle.baffle_curve.GetLength(), 2),
                        "depth": baffle.depth,
                        "name": baffle.name,
                        "parent_centerline_name": baffle.baffle_centerline.name,
                        "parent_centerline_guid": str(obj.Id),  # Add GUID of the parent centerline
                        "parent_centerline_object": baffle.baffle_centerline  # Keep Python object in DataFrame
                    })

        # Create Polars DataFrame
        if baffle_data_list:
            baffle_df = pl.DataFrame(baffle_data_list)
            os.makedirs(os.path.dirname(data_path), exist_ok=True)  # Ensure directory exists

            # Write only serializable columns to JSON
            baffle_df.select(["length", "depth", "name", "centerline_name", "centerline_guid"]).write_json(data_path, row_oriented=True)
            print(f"Baffle data written to {data_path}")
            return baffle_df
        else:
            # Write an empty JSON file if no data is found
            with open(data_path, 'w') as f:
                json.dump([], f)
            print(f"No baffle data found. Empty JSON written to {data_path}")
            return pl.DataFrame()
    except Exception as e:
        print(f"Error collecting baffle data: {e}")
        return pl.DataFrame()


def get_project_root():
    """Returns the root directory of the project"""
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def get_data_path(filename):
    """Returns the full path to a file in the data directory"""
    project_root = get_project_root()
    return os.path.join(project_root, "code", "data", filename)


def get_rhino_python_path():
    """Returns the dynamically determined path to the Rhino 8 Python executable"""
    user_profile = os.getenv('USERPROFILE')
    if not user_profile:
        print("Error: USERPROFILE environment variable not found.")
        # Consider raising an exception or returning a more specific error
        return None 
    
    # Construct the path using os.path.join for cross-platform compatibility (though targeting Windows here)
    rhino_python_path = os.path.join(user_profile, '.rhinocode', 'py39-rh8', 'pythonw.exe')
    
    # Optional: Check if the path actually exists
    if not os.path.exists(rhino_python_path):
        print(f"Warning: Rhino Python executable not found at expected path: {rhino_python_path}")
        # Depending on requirements, you might return None or the path anyway
        # return None 
    
    return rhino_python_path


class DataOutput:
    pass
