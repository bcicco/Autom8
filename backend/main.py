import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import fastapi
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
import time
import base64
from deepseekClient import DeepSeekClient
from config import settings

app = fastapi.FastAPI()

active_connections = {}
agents = {}
main_event_loop = None  # Store the main event loop

from pydantic import BaseModel


class TriggerRequest(BaseModel):
    url: str
    user_id: str


class UserInputResponse(BaseModel):
    user_id: str
    value: str


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def display_agent_udates(interval_seconds: int):
    while True:
        try:
            for user_id, agent in agents.items():
                if agent.status == "updated":
                    await send_screenshot(user_id, "agent status updated")
                    agent.status = "asleep"

        except Exception as e:
            print(f"Error in timer task: {e}")
        await asyncio.sleep(interval_seconds)


@app.get("/healthCheck")
def health_check():
    return {"status": "ok"}


@app.on_event("startup")
async def start_timer():
    global main_event_loop
    main_event_loop = asyncio.get_event_loop()
    asyncio.create_task(display_agent_udates(2))


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    active_connections[user_id] = websocket
    print(f"WebSocket connected: {user_id}")

    try:
        while True:
            data = await websocket.receive_json()
            print(f"Received from {user_id}: {data}")

            # Handle user input responses
            if data.get("type") == "user_input_response":
                if user_id in agents:
                    agents[user_id].provide_user_input(data.get("value"))
                    print(f"Provided user input to agent: {data.get('value')}")

                    # Send screenshot immediately after user provides input
                    await send_screenshot(user_id, "Processing user input...")

    except WebSocketDisconnect:
        del active_connections[user_id]
        print(f"WebSocket disconnected: {user_id}")


@app.post("/trigger")
def trigger_endpoint(request: TriggerRequest):
    print(f"Triggered action with URL: {request.url} and session {request.user_id}")

    def start_agent():
        try:
            print(f"Starting agent for user {request.user_id}")
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            # chrome_options.add_argument("--headless=new")

            driver = webdriver.Chrome(options=chrome_options)

            # Create send_message callback for this user
            async def send_to_user(data: dict):
                await send_message(request.user_id, data)

                # If it's a user input request, also send screenshot immediately
                if data.get("type") == "user_input_request":
                    await send_screenshot(request.user_id, "Waiting for user input...")

            agents[request.user_id] = DeepSeekClient(
                settings.DEEP_SEEK_API_KEY,
                driver,
                send_message_callback=send_to_user,
                main_loop=main_event_loop,  # Use the stored main loop
            )

            agents[request.user_id].start(request)

        except Exception as e:
            print(f"Error in browser automation: {e}")
            import traceback

            traceback.print_exc()

    # Start agent in a separate thread
    thread = threading.Thread(target=start_agent)
    thread.start()

    return {"status": "triggered", "user_id": request.user_id}


async def send_screenshot(user_id: str, message: str = ""):
    """Capture screenshot and send to specific user's websocket"""
    try:
        if user_id in agents and user_id in active_connections:
            screenshot = agents[user_id].driver.get_screenshot_as_png()
            b64_screenshot = base64.b64encode(screenshot).decode()

            await active_connections[user_id].send_json(
                {"type": "screenshot", "data": b64_screenshot, "message": message}
            )

            print(f"Sent screenshot to {user_id}: {message}")
            agents[user_id].status = "processing"
    except Exception as e:
        print(f"Error sending screenshot: {e}")


async def send_message(user_id: str, data: dict):
    """Send any message to specific user"""
    try:
        if user_id in active_connections:
            await active_connections[user_id].send_json(data)
            print(f"Sent message to {user_id}: {data.get('type')}")
    except Exception as e:
        print(f"Error sending message: {e}")
