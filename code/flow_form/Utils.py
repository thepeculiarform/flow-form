import Rhino as rh
import Rhino.Geometry as rg
import scriptcontext as sc
import subprocess
import psutil
import os
import sys  # Add this import

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


def manage_streamlit_server(action="start", port=8501):
    """Manages the Streamlit server process"""
    streamlit_script = os.path.join(os.path.dirname(__file__), "..", "interface", "app.py")
    pid_file = os.path.join(os.path.dirname(__file__), "..", "interface", "streamlit.pid")
    
    if action == "start":
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

        # Start new process
        try:
            process = subprocess.Popen(
                ["streamlit", "run", streamlit_script, "--server.port", str(port)],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            
            # Save PID to file
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
                
            print(f"Started Streamlit server on port {port} (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"Error starting Streamlit: {e}")
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

class DataOutput:
    pass



