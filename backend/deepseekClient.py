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


class Option(BaseModel):
    value: str
    label: str
    selected: Optional[bool] = False


class FormField(BaseModel):
    name: str
    type: str
    label: Optional[str] = None
    options: Optional[List[Option]] = None
    required: bool = False
    placeholder: Optional[str] = None
    current_value: Optional[str] = None
    id: Optional[str] = None
    css_selector: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    disabled: bool = False
    readonly: bool = False


class ButtonInfo(BaseModel):
    text: str
    css_selector: str
    button_type: str  # e.g., "submit", "button", "close", "link"
    id: Optional[str] = None
    classes: Optional[str] = None
    aria_label: Optional[str] = None


class FormSchema(BaseModel):
    fields: List[FormField]
    buttons: List[ButtonInfo] = []
    submit_button_text: Optional[str] = None
    submit_button_selector: Optional[str] = None
    form_action: Optional[str] = None
    form_method: Optional[str] = None
    other_context: Optional[str] = None


class ActionSchema(BaseModel):
    action_type: Literal[
        "fill_form",
        "click_button",
        "select_option",
        "check_checkbox",
        "wait",
        "navigate",
        "request_user_input",
    ]
    parameters: Dict[str, Any]
    reasoning: Optional[str] = None


class UserInputRequest(BaseModel):
    field_name: str
    prompt: str
    input_type: Literal["text", "code", "choice", "confirmation"]
    options: Optional[List[str]] = None
    css_selector: Optional[str] = None


class DecisionResponse(BaseModel):
    actions: List[ActionSchema] = []
    status: Literal[
        "ready_to_submit",
        "needs_input",
        "error",
        "complete",
        "navigation_needed",
        "awaiting_user_input",
    ]
    message: str
    missing_fields: Optional[List[str]] = None
    user_input_request: Optional[UserInputRequest] = None


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
        self.main_loop = main_loop  # Store reference to main event loop
        self.pending_user_input = None

        # USE THREADING EVENT INSTEAD OF ASYNCIO EVENT
        self.user_input_received = threading.Event()
        self.user_input_value = None  # Initialize as None
        self.event_loop = None  # Store reference to the agent's event loop

    def clean_json_response(self, content: str) -> str:
        """Clean the LLM response to extract valid JSON"""
        # Remove markdown code blocks if present
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*$", "", content)

        # Strip leading/trailing whitespace
        content = content.strip()

        return content

    def truncate_html(self, html_content: str, max_chars: int = 50000) -> str:
        """Truncate HTML to prevent token limit issues while keeping important parts"""
        if len(html_content) <= max_chars:
            return html_content

        # Try to keep the important parts - forms, inputs, buttons
        # Split and prioritize form-related content
        truncated = html_content[:max_chars]

        # Try to end at a complete tag
        last_tag = truncated.rfind(">")
        if last_tag > max_chars * 0.8:  # Only if we're not losing too much
            truncated = truncated[: last_tag + 1]

        return truncated

    def analyze_form_html(self, html_content: str) -> FormSchema:
        """Extract form schema from HTML using DeepSeek with JSON output"""

        # Truncate HTML to prevent response cutoff
        html_content = self.truncate_html(html_content)

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert at analyzing webpages, especially HTML forms. Extract all form fields with their properties AND all clickable buttons on the page.

IMPORTANT: 
- Look for the 'value' attribute in form fields to capture pre-filled values.
- Detect ALL buttons including: submit buttons, regular buttons, close buttons (X), modal dismiss buttons, navigation buttons, etc.
- For buttons, capture their text content, CSS selectors, type, and any identifying attributes.
- CRITICAL: Keep your response concise. Only extract the ESSENTIAL form fields and buttons. Don't include every single element if there are many.
- Prioritize: visible input fields, submit buttons, navigation buttons, and form controls the user needs to interact with.

Return your response as a JSON object in this exact format (no markdown, no explanation):
{
    "fields": [
        {
            "name": "field_name",
            "type": "text",
            "label": "Field Label",
            "options": [
                {"value": "option1", "label": "Option 1", "selected": true},
                {"value": "option2", "label": "Option 2", "selected": false}],
            "required": false,
            "placeholder": "Enter text",
            "current_value": null,
            "id": "element_id",
            "css_selector": "input[name='field_name']",
            "min_length": null,
            "max_length": null,
            "pattern": null,
            "disabled": false,
            "readonly": false
        }
    ],
    "buttons": [
        {
            "text": "Launch Form",
            "css_selector": "button#launch-btn",
            "button_type": "button",
            "id": "launch-btn",
            "classes": "btn btn-primary",
            "aria_label": "Launch application form"
        },
        {
            "text": "×",
            "css_selector": "button.close",
            "button_type": "close",
            "id": null,
            "classes": "close",
            "aria_label": "Close"
        }
    ],
    "submit_button_text": "Submit",
    "submit_button_selector": "button[type='submit']",
    "form_action": "/submit",
    "form_method": "POST",
    "other_context": "context that might be useful if a bot was trying to understand the state of the webpage, including any visible modals, popups, or overlays"
}

Note: 
- current_value should contain the value attribute of the input field if present, otherwise null.
- buttons array should include ALL clickable buttons found on the page, not just submit buttons.
- button_type should indicate the purpose: "submit", "button", "close", "link", "navigation", etc.""",
                },
                {
                    "role": "user",
                    "content": f"Analyze this HTML and extract ONLY the essential form input fields AND important buttons (submit, navigation, close). Keep response under 10KB. Return as JSON:\n\n{html_content}",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=4000,  # Limit response size
        )

        raw_content = response.choices[0].message.content
        print("=" * 60)
        print("RAW LLM RESPONSE (analyze_form_html):")
        print(raw_content[:500])  # Print first 500 chars
        print("=" * 60)

        try:
            cleaned_content = self.clean_json_response(raw_content)
            json_response = json.loads(cleaned_content)
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
                    for action in self.action_history[-10:]  # Only last 10 actions
                ]
            )
            if self.action_history
            else "No actions taken yet"
        )

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": """You are an intelligent form-filling assistant. Analyze the webpage and decide what SEQUENCE of actions to take to complete it. 

Available user data:
- username: "ben.cicco@yahoo.com"
- password: "Ben10%123098765"


Action types:
- fill_form: Fill text/email/password fields
- select_option: Select from dropdown
- check_checkbox: Check/uncheck checkbox
- click_button: Click any button (submit, close, launch, navigation, etc.)
- wait: Wait for page to load
- navigate: Navigate to different URL
- request_user_input: Request information from user (use when you need data not in available user data)

Input types: 
'text', 'code', 'choice' or 'confirmation'

CRITICAL RULES:

1. Return a SEQUENCE of all actions needed to complete the current task
2. For each action, you MUST provide the css_selector from the form/button data
3. HANDLE BLOCKING ELEMENTS FIRST: If there are popups, modals, or overlays (like close buttons with X), click them FIRST before filling forms
4. NAVIGATION: If you see buttons like "Launch Form" or "Start Application" that need to be clicked to reveal the form, click them first
5. Process fields in logical order: handle blocking elements → navigation → fill all input fields → select dropdowns → checkboxes → click submit
6. If you encounter fields that require information NOT in the available user data (like 2FA codes, verification codes, or missing personal info), use "request_user_input" action
7. When requesting user input, provide clear prompts and specify the input type
8. Do NOT repeat actions that have already been taken (check action history)
9. If ALL required fields are already filled and the form has been successfully submitted, return status "complete" with empty actions array

CRITICAL FOR TIME-SENSITIVE AUTHENTICATION CODES:
10. When requesting authentication codes (2FA, OTP, verification codes), you MUST include ALL subsequent actions in the SAME action sequence
11. Example sequence: [request_user_input for code] → [fill_form with code] → [click_button to submit]
12. DO NOT stop after request_user_input - continue with all remaining actions that use that input
13. The user will provide the value, and ALL actions will execute in rapid succession without re-analyzing the page
14. This prevents authentication codes from expiring before submission

CRITICAL: When you include a "request_user_input" action, you MUST ALSO populate the "user_input_request" field at the top level of your response with the same information.

For click_button actions, use the css_selector from the buttons array in the form data.

Return your response as a JSON object. Example with user input request AND subsequent actions:
{
    "actions": [
        {
            "action_type": "request_user_input",
            "parameters": {
                "field_name": "verification_code",
                "css_selector": "input[name='code']"
            },
            "reasoning": "Need 2FA code from user"
        },
        {
            "action_type": "fill_form",
            "parameters": {
                "field_name": "verification_code",
                "css_selector": "input[name='code']",
                "value": "USER_INPUT"
            },
            "reasoning": "Fill the verification code field with user-provided value"
        },
        {
            "action_type": "click_button",
            "parameters": {
                "selector": "button[type='submit']",
                "text": "Verify"
            },
            "reasoning": "Submit the form immediately after filling code"
        }
    ],
    "status": "awaiting_user_input",
    "message": "Waiting for verification code, then will auto-submit",
    "missing_fields": ["verification_code"],
    "user_input_request": {
        "field_name": "verification_code",
        "prompt": "Please enter the 6-digit verification code sent to your email or phone. It will be submitted immediately.",
        "input_type": "code",
        "css_selector": "input[name='code']"
    }
}

NOTE: The "user_input_request" field is REQUIRED when you have a "request_user_input" action. It must contain:
- field_name: name of the field
- prompt: clear instruction for the user
- input_type: "text", "code", "choice", or "confirmation"
- css_selector: the CSS selector for the input field
- options: (optional) list of choices if input_type is "choice"

Status options: ready_to_submit, needs_input, error, complete, navigation_needed, awaiting_user_input""",
                },
                {
                    "role": "user",
                    "content": f"""Analyze this webpage and decide what SEQUENCE of actions to take. Return as JSON:

WEBPAGE DATA (including all buttons and form fields):
{form_info}

ACTION HISTORY (DO NOT REPEAT THESE):
{history_str}

What sequence of actions should be taken to complete this task?""",
                },
            ],
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content
        print("=" * 60)
        print("RAW LLM RESPONSE (make_decision):")
        print(raw_content[:500])  # Print first 500 chars
        print("=" * 60)

        try:
            cleaned_content = self.clean_json_response(raw_content)
            json_response = json.loads(cleaned_content)
            print("LLM DECISION RESPONSE:")
            print(json.dumps(json_response, indent=2))
            print("=" * 60)
            return DecisionResponse(**json_response)
        except json.JSONDecodeError as e:
            print(f"JSON DECODE ERROR: {e}")
            print(f"Problematic content around error:")
            print(raw_content[max(0, e.pos - 100) : min(len(raw_content), e.pos + 100)])
            raise

    async def request_user_input(self, input_request: UserInputRequest):
        """Request input from user via WebSocket and wait for response"""
        print(f"\nRequesting user input: {input_request.prompt}")
        print(f"send_message_callback: {self.send_message_callback}")
        print(f"main_loop: {self.main_loop}")

        # Set status to trigger screenshot update
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

    def provide_user_input(self, value: str):
        """Called when user provides input via WebSocket (from different thread)"""
        print(f"Received user input: {value}")
        self.user_input_value = value
        self.user_input_received.set()
        print("Event set - unblocking request_user_input")

    async def execute_actions(self, decision: DecisionResponse):
        """Execute a sequence of actions"""

        if not decision.actions:
            print("No actions to execute")
            return

        print(f"\nExecuting {len(decision.actions)} actions in sequence:")

        # Track user input value for placeholder replacement
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

    async def run_async(self, url: str, user_id: str):
        """Async version of run method"""
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
