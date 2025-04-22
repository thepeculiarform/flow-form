from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import threading

class BaffleEdit(BaseModel):
    guid: str
    property: str
    value: float

class APIServer:
    def __init__(self, port=8000):
        self.port = port
        self.app = FastAPI()
        self._is_running = False
        
        @self.app.post("/edit")
        async def handle_edit(edit: BaffleEdit):
            print(f"Received edit: {edit}")  # Simple print instead of logging
            return {"status": "success"}
            
        @self.app.get("/status")
        async def get_status():
            return {"running": self._is_running, "port": self.port}

    def start(self):
        if not self._is_running:
            self.server_thread = threading.Thread(
                target=lambda: uvicorn.run(
                    self.app, 
                    host="127.0.0.1", 
                    port=self.port
                ),
                daemon=True
            )
            self.server_thread.start()
            self._is_running = True
            return True
        return False