
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import json

# Define get_data_path locally
def get_data_path(filename):
    """Returns the full path to a file in the data directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.abspath(os.path.join(current_dir, "..")), "data")
    os.makedirs(data_dir, exist_ok=True)  # Ensure the data directory exists
    return os.path.join(data_dir, filename)

# Test the function
print(f"Data path for 'baffle_edits_in.json': {get_data_path('baffle_edits_in.json')}")

# FastAPI app setup
class BaffleData(BaseModel):
    guid: str
    centerline_name: str
    depth: float
    length: float
    type: str

class BaffleEdit(BaseModel):
    guid: str
    property: str
    value: float

app = FastAPI()

@app.get("/status")
async def get_status():
    return {"status": "running"}

@app.get("/baffles")
async def get_baffles():
    """Endpoint for Streamlit to get current baffle data"""
    data_path = get_data_path("baffle_data.json")
    try:
        if os.path.exists(data_path):
            with open(data_path, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    # Handle invalid JSON
                    raise HTTPException(status_code=500, detail="Invalid JSON in baffle_data.json")
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading baffle data: {str(e)}")

@app.post("/edit")
async def handle_edit(edit: BaffleEdit):
    """Endpoint for Streamlit to send baffle edits"""
    edits_path = get_data_path("baffle_edits_in.json")
    try:
        edits = [edit.dict()]
        with open(edits_path, 'w') as f:
            json.dump(edits, f, indent=2)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add direct execution test
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)