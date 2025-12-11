import os
from openai import OpenAI
from config import settings
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import threading
from typing import Literal
import time
import asyncio
import re
from helpers.deepseekHelpers import (
    generate_system_prompt_html,
    generate_system_prompt_decision,
)
from models.LLMSchema import FormSchema, DecisionResponse, UserInputRequest


class DeepSeekClient:
    def __init__(
        self, api_key: str, driver, send_message_callback=None, main_loop=None
    ):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.driver = driver
        self.status = "asleep"
        self.website_status = ""
        self.username = "ben"
        self.password = "password123"
        self.action_history = []
        self.user_data = {
            "email": "ben@example.com",
            "phone": "+1234567890",
            "first_name": "Ben",
            "last_name": "Smith",
            "address": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94102",
            "country": "USA",
        }
        self.send_message_callback = send_message_callback
        self.main_loop = main_loop  #  Reference to main event loop running in main.py
        self.pending_user_input = None

        # USE THREADING EVENT INSTEAD OF ASYNCIO EVENT
        self.user_input_received = threading.Event()
        self.user_input_value = None
        self.event_loop = None  #  Reference to the agent's event loop

    # --- LLM CALLS ---

    def analyze_form_html(self, html_content: str) -> FormSchema:
        """Extract form schema from HTML using DeepSeek with JSON output"""

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=generate_system_prompt_html(html_content),
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content
        print("=" * 60)
        print("RAW LLM RESPONSE (analyze_form_html):")
        print(raw_content[:500])
        print("=" * 60)

        try:
            json_response = json.loads(raw_content)
            print(json.dumps(json_response, indent=2))
            return FormSchema(**json_response)
        except json.JSONDecodeError as e:
            print(f"JSON DECODE ERROR: {e}")
            print(f"Problematic content around error:")
            print(raw_content[max(0, e.pos - 100) : min(len(raw_content), e.pos + 100)])
            raise

    def make_decision(self, website_status: FormSchema) -> DecisionResponse:
        """Analyze the form schema and decide what sequence of actions to take"""

        form_info = website_status.model_dump_json(indent=2)

        history_str = (
            "\n".join(
                [
                    f"- {action.action_type}: {action.parameters.get('field_name', action.parameters.get('text', 'N/A'))} = {action.parameters.get('value', action.parameters.get('selector', 'N/A'))}"
                    for action in self.action_history[-10:]
                ]
            )
            if self.action_history
            else "No actions taken yet"
        )

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=generate_system_prompt_decision(form_info, history_str),
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content
        print("=" * 60)
        print("RAW LLM RESPONSE (make_decision):")
        print(raw_content[:500])
        print("=" * 60)

        try:

            json_response = json.loads(raw_content)
            print("LLM DECISION RESPONSE:")
            print(json.dumps(json_response, indent=2))
            print("=" * 60)
            return DecisionResponse(**json_response)
        except json.JSONDecodeError as e:
            print(f"JSON DECODE ERROR: {e}")
            print(f"Problematic content around error:")
            print(raw_content[max(0, e.pos - 100) : min(len(raw_content), e.pos + 100)])
            raise

    # --- REQUEST + HANDLE USER INPUT ---

    async def request_user_input(self, input_request: UserInputRequest):
        """Request input from user via WebSocket and wait for response"""
        print(f"\nRequesting user input: {input_request.prompt}")
        print(f"send_message_callback: {self.send_message_callback}")
        print(f"main_loop: {self.main_loop}")

        self.status = "updated"

        if self.send_message_callback and self.main_loop:
            print("Attempting to send user input request to frontend...")
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.send_message_callback(
                        {
                            "type": "user_input_request",
                            "data": {
                                "field_name": input_request.field_name,
                                "prompt": input_request.prompt,
                                "input_type": input_request.input_type,
                                "options": input_request.options,
                            },
                        }
                    ),
                    self.main_loop,
                )
                result = future.result(timeout=5)
                print(f"User input request sent to frontend successfully: {result}")
            except Exception as e:
                print(f"Failed to send user input request: {e}")
                import traceback

                traceback.print_exc()
        else:
            print(
                f"Cannot send message - callback: {self.send_message_callback is not None}, loop: {self.main_loop is not None}"
            )

        self.pending_user_input = input_request
        self.user_input_received.clear()

        print("Waiting for user input...")

        try:
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, self.user_input_received.wait), timeout=300
            )
            print(f"User input received: {self.user_input_value}")
            self.status = "updated"
            return self.user_input_value
        except asyncio.TimeoutError:
            print("Timeout waiting for user input")
            raise Exception("User input timeout")

    # provide_user_input only called externally, allows external to provide input without weird timing
    def provide_user_input(self, value: str):
        """Called when user provides input via WebSocket (from different thread)"""
        print(f"Received user input: {value}")
        self.user_input_value = value
        self.user_input_received.set()
        print("Event set - unblocking request_user_input")

    # Nothing pretty here, giant elif statement to call tool based on response

    async def execute_actions(self, decision: DecisionResponse):
        """Execute a sequence of actions"""

        if not decision.actions:
            print("No actions to execute")
            return

        print(f"\nExecuting {len(decision.actions)} actions in sequence:")

        user_input_value = None

        for i, action in enumerate(decision.actions, 1):
            try:
                print(f"\n[{i}/{len(decision.actions)}] {action.action_type}")
                print(f"  Reasoning: {action.reasoning}")

                if action.action_type == "fill_form":
                    params = action.parameters.copy()
                    if (
                        params.get("value") == "USER_INPUT"
                        and user_input_value is not None
                    ):
                        params["value"] = user_input_value
                        print(
                            f"  Replacing USER_INPUT placeholder with: {user_input_value}"
                        )

                    self._fill_field(params)
                    self.action_history.append(action)

                elif action.action_type == "select_option":
                    self._select_option(action.parameters)
                    self.action_history.append(action)

                elif action.action_type == "check_checkbox":
                    self._check_checkbox(action.parameters)
                    self.action_history.append(action)

                elif action.action_type == "click_button":
                    self._click_button(action.parameters)
                    self.action_history.append(action)

                elif action.action_type == "wait":
                    self._wait(action.parameters)
                    self.action_history.append(action)

                elif action.action_type == "navigate":
                    self._navigate(action.parameters)
                    self.action_history.append(action)

                elif action.action_type == "request_user_input":
                    print(f"DEBUG: request_user_input action triggered")
                    print(
                        f"DEBUG: decision.user_input_request = {decision.user_input_request}"
                    )

                    if decision.user_input_request:
                        print(
                            f"DEBUG: Calling request_user_input with: {decision.user_input_request}"
                        )
                        user_input_value = await self.request_user_input(
                            decision.user_input_request
                        )
                        print(f"DEBUG: Stored user_input_value: {user_input_value}")
                    else:
                        print(
                            "DEBUG: decision.user_input_request is None! Cannot request user input."
                        )

                print(f"   Success")
                time.sleep(0.3)

            except Exception as e:
                print(f"   Failed: {e}")
                raise

    #   --- AGENT TOOLS  ---
    def _fill_field(self, params: Dict[str, Any]):
        """Fill a text input field"""
        css_selector = params.get("css_selector")
        value = params.get("value")

        if not css_selector:
            raise Exception("css_selector is required in parameters")

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
        element.clear()
        element.send_keys(value)

    def _select_option(self, params: Dict[str, Any]):
        """Select an option from a dropdown"""
        css_selector = params.get("css_selector")
        value = params.get("value")

        if not css_selector:
            raise Exception("css_selector is required in parameters")

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
        select = Select(element)
        select.select_by_visible_text(value)

    def _check_checkbox(self, params: Dict[str, Any]):
        """Check or uncheck a checkbox"""
        css_selector = params.get("css_selector")
        checked = params.get("checked", True)

        if not css_selector:
            raise Exception("css_selector is required in parameters")

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
        if element.is_selected() != checked:
            element.click()

    def _click_button(self, params: Dict[str, Any]):
        """Click a button"""
        selector = params.get("selector") or params.get("css_selector")
        text = params.get("text")

        if selector:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
        elif text:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//button[contains(text(), '{text}')]")
                )
            )
        else:
            raise Exception("Must provide either selector or text for button")

        element.click()

    def _wait(self, params: Dict[str, Any]):
        """Wait for specified time or condition"""
        seconds = params.get("seconds", 2)
        time.sleep(seconds)

    def _navigate(self, params: Dict[str, Any]):
        """Navigate to a URL"""
        url = params.get("url")
        self.driver.get(url)

    # --- RUN & START ----
    async def run_async(self, url: str, user_id: str):
        """Main run method"""
        self.event_loop = asyncio.get_event_loop()

        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            print("Page loaded successfully")

            max_iterations = 10
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                print(f"\n{'='*60}")
                print(f"ITERATION {iteration}")
                print(f"{'='*60}")

                html_content = self.driver.page_source
                self.website_status = self.analyze_form_html(html_content)

                decision = self.make_decision(self.website_status)
                print(f"\nStatus: {decision.status}")
                print(f"Message: {decision.message}")

                if decision.status == "complete":
                    print("\nForm automation completed successfully!")
                    self.status = "completed"
                    break

                if decision.actions:
                    await self.execute_actions(decision)
                    self.status = "updated"
                    await asyncio.sleep(1.5)
                else:
                    print("No actions returned but status is not complete")
                    break

            if iteration >= max_iterations:
                print("\nMax iterations reached - stopping to prevent infinite loop")
                self.status = "error"

        except Exception as e:
            print(f"\nError in browser automation: {e}")
            import traceback

            traceback.print_exc()
            self.status = "error"

    def start(self, request):
        """Start the agent in a new thread"""
        print(f"Starting browser launch thread for URL: {request.url}")

        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run_async(request.url, request.user_id))
            loop.close()

        thread = threading.Thread(target=run_in_thread)
        thread.start()
