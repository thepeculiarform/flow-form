import asyncio
import websockets
import json
from queue import Queue
import threading
import socket

class BaffleWebsocketServer:
    def __init__(self, port=8765):
        self.port = port
        self.connected_clients = set()
        self.message_queue = Queue()
        self.server = None
        self._is_running = False
        
    @property
    def is_running(self):
        return self._is_running

    def _check_port_available(self):
        """Check if port is available before starting server"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', self.port))
                return True
            except socket.error:
                return False

    async def handler(self, websocket):
        self.connected_clients.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                # Handle incoming edits from Streamlit
                if data.get('type') == 'edit':
                    self.message_queue.put(data)
                    await websocket.send(json.dumps({'type': 'ack', 'status': 'received'}))
        finally:
            self.connected_clients.remove(websocket)

    async def broadcast_updates(self, data):
        if self.connected_clients:
            message = json.dumps(data)
            await asyncio.gather(
                *[client.send(message) for client in self.connected_clients]
            )

    def start_server(self):
        if self.is_running:
            print(f"Server already running on port {self.port}")
            return False
            
        if not self._check_port_available():
            print(f"Port {self.port} is in use. Please try a different port.")
            return False

        async def serve():
            try:
                self.server = await websockets.serve(self.handler, "localhost", self.port)
                self._is_running = True
                print(f"Server started on port {self.port}")
                await self.server.wait_closed()
            except Exception as e:
                print(f"Server error: {e}")
                self._is_running = False

        def run_async():
            asyncio.run(serve())

        self.thread = threading.Thread(target=run_async, daemon=True)
        self.thread.start()
        return True

    def stop_server(self):
        if self.server:
            self.server.close()
            self._is_running = False
            print(f"Server stopped on port {self.port}")