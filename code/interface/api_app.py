from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn


app = FastAPI()

class BaffleEdit(BaseModel):
    guid: str
    property: str
    value: float

@app.get("/status")
async def get_status():
    return {"status": "running"}

@app.post("/edit")
async def handle_edit(edit: BaffleEdit):
    print(f"Received edit: {edit}")
    return {"status": "success"}

# Add direct execution test
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)