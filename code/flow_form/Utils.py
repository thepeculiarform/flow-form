import Rhino as rh
import Rhino.Geometry as rg
import scriptcontext as sc
import subprocess
import psutil
import os
import System
import time


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
    # Get Rhino Python executable
    rhino_python = r"C:\Users\jason\.rhinocode\py39-rh8\python.exe"
    
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
            return True
        return False
    except Exception as e:
        print(f"Error updating UserText: {e}")
        return False

def process_baffle_edits():
    """Process edits from Streamlit and update Rhino objects"""
    # Use consistent path handling
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    edits_file = os.path.join(project_root, "code", "data", "baffle_edits_in.json")
    print(f"Checking for edits file: {edits_file}")
    
    if os.path.exists(edits_file):
        try:
            with open(edits_file, 'r') as f:
                edits = json.load(f)
                print(f"Loaded edits from file:")
                print(json.dumps(edits, indent=2))
                
                for edit in edits:
                    guid_str = edit['guid']
                    try:
                        # Convert string GUID to System.Guid
                        guid = System.Guid.Parse(guid_str)
                        # Verify object exists before update
                        obj = sc.doc.Objects.Find(guid)
                        if obj:
                            print(f"Found object {guid_str}")
                            if update_object_usertext(
                                guid,  # Now passing System.Guid object
                                edit['property'],
                                edit['value']
                            ):
                                print(f"Successfully updated {guid_str}")
                            else:
                                print(f"Failed to update {guid_str}")
                        else:
                            print(f"Object not found: {guid_str}")
                    except System.ArgumentNullException:
                        print(f"Invalid GUID format: {guid_str}")
                        
            os.remove(edits_file)  # Clear processed edits
            return True
        except Exception as e:
            print(f"Error processing edits: {e}")
            import traceback
            traceback.print_exc()
            return False
    return False


class DataOutput:
    pass

# from .websocket_server import BaffleWebsocketServer

# class BaffleManager:
#     def __init__(self, port=8765):
#         """Initialize BaffleManager with optional port
#         Args:
#             port (int): Port number for WebSocket server (default: 8765)
#         """
#         self.ws_server = BaffleWebsocketServer(port=port)
#         self._is_running = False
        
#     @property
#     def is_running(self):
#         return self._is_running
        
#     def start(self):
#         """Start the WebSocket server"""
#         success = self.ws_server.start_server()
#         if success:
#             self._is_running = True
#         return success
        
#     def stop(self):
#         """Stop the WebSocket server"""
#         self.ws_server.stop_server()
#         self._is_running = False
        
#     def process_edits(self):
#         """Process any pending edits from WebSocket queue"""
#         while not self.ws_server.message_queue.empty():
#             edit = self.ws_server.message_queue.get()
#             if edit.get('type') == 'edit':
#                 guid = System.Guid.Parse(edit['guid'])
#                 update_object_usertext(guid, edit['property'], edit['value'])
                
#     def broadcast_update(self, data):
#         """Send updates to Streamlit clients"""
#         asyncio.run(self.ws_server.broadcast_updates({
#             'type': 'update',
#             'data': data
#         }))



