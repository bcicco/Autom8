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


class FormField(BaseModel):
    name: str
    type: str  # text, email, password, select, checkbox, radio, textarea, tel, url, number, date, file, hidden
    label: Optional[str] = None
    options: Optional[List[str]] = None  # For dropdowns/radio buttons
    required: bool = False
    placeholder: Optional[str] = None
    current_value: Optional[str] = None
    id: Optional[str] = None  # DOM element ID
    css_selector: Optional[str] = None  # CSS selector to locate element
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern for validation
    disabled: bool = False
    readonly: bool = False


class FormSchema(BaseModel):
    fields: List[FormField]
    submit_button_text: Optional[str] = None
    submit_button_selector: Optional[str] = None
    form_action: Optional[str] = None  # Form submission URL
    form_method: Optional[str] = None  # GET or POST
    other_context: Optional[str] = None


class ActionSchema(BaseModel):
    action_type: Literal[
        "fill_form",
        "click_button",
        "select_option",
        "check_checkbox",
        "wait",
        "navigate",
    ]
    parameters: Dict[str, Any]
    reasoning: Optional[str] = None  # Why this action was chosen


class DecisionResponse(BaseModel):
    action: Optional[ActionSchema] = None  # Made optional for when complete
    status: Literal[
        "ready_to_submit", "needs_input", "error", "complete", "navigation_needed"
    ]
    message: str
    missing_fields: Optional[List[str]] = None


class DeepSeekClient:
    def __init__(self, api_key: str, driver):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.driver = driver
        self.status = "asleep"
        self.website_status = ""
        self.username = "ben"
        self.password = "password123"
        self.action_history = []  # Track all actions taken
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

    def analyze_form_html(self, html_content: str) -> FormSchema:
        """Extract form schema from HTML using DeepSeek with JSON output"""

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert at analyzing HTML forms. Extract all form fields with their properties.

IMPORTANT: Look for the 'value' attribute in form fields to capture pre-filled values.

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{
    "fields": [
        {
            "name": "field_name",
            "type": "text",
            "label": "Field Label",
            "options": null,
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
    "submit_button_text": "Submit",
    "submit_button_selector": "button[type='submit']",
    "form_action": "/submit",
    "form_method": "POST",
    "other_context": "context that might be useful if a bot was trying to understand the state of the webpage"
}

Note: current_value should contain the value attribute of the input field if present, otherwise null.""",
                },
                {
                    "role": "user",
                    "content": f"Analyze this HTML and extract all form input fields:\n\n{html_content[:10000]}",
                },
            ],
            response_format={"type": "json_object"},
        )

        json_response = json.loads(response.choices[0].message.content)
        return FormSchema(**json_response)

    def make_decision(self, website_status: FormSchema) -> DecisionResponse:
        """Analyze the form schema and decide what single action to take"""

        form_info = website_status.model_dump_json(indent=2)

        # Format action history for context
        history_str = (
            "\n".join(
                [
                    f"- {action.action_type}: {action.parameters.get('field_name', 'N/A')} = {action.parameters.get('value', action.parameters.get('text', 'N/A'))}"
                    for action in self.action_history
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
                    "content": """You are an intelligent form-filling assistant. Analyze the form and decide what SINGLE action to take next.

Available user data:
- username: "ben"
- password: "password123"
- email: "ben@example.com"
- phone: "+1234567890"
- first_name: "Ben"
- last_name: "Smith"
- address: "123 Main St"
- city: "San Francisco"
- state: "CA"
- zip: "94102"
- country: "USA"

Action types:
- fill_form: Fill text/email/password fields
- select_option: Select from dropdown
- check_checkbox: Check/uncheck checkbox
- click_button: Click submit or other buttons
- wait: Wait for page to load
- navigate: Navigate to different URL

CRITICAL RULES:
1. Return ONLY ONE action at a time - this will be called repeatedly
2. For each action, you MUST provide the css_selector from the form field data
3. Check the action history below - NEVER repeat an action you've already taken
4. If you see a field in the action history, skip it completely
5. If ALL required fields are filled AND THE FORM HAS BEEN SUBMITTED (check action history), return status "complete" with no action
6. Process fields in order: fill all fields first, then click submit button

Return ONLY valid JSON:
{
    "action": {
        "action_type": "fill_form",
        "parameters": {
            "field_name": "username",
            "css_selector": "input[name='username']",
            "value": "ben"
        },
        "reasoning": "Filling empty username field with provided username"
    },
    "status": "needs_input",
    "message": "Filling username field",
    "missing_fields": []
}

OR when complete:
{
    "action": null,
    "status": "complete",
    "message": "All fields filled successfully",
    "missing_fields": []
}

Status options: ready_to_submit, needs_input, error, complete, navigation_needed""",
                },
                {
                    "role": "user",
                    "content": f"""Analyze this form and decide what SINGLE action to take next:

FORM DATA:
{form_info}

ACTION HISTORY (DO NOT REPEAT THESE):
{history_str}

What is the next action to take?""",
                },
            ],
            response_format={"type": "json_object"},
        )

        json_response = json.loads(response.choices[0].message.content)
        return DecisionResponse(**json_response)

    def execute_action(self, decision: DecisionResponse):

        action = decision.action
        if not action:
            print("No action to execute")
            return

        try:
            if action.action_type == "fill_form":
                self._fill_field(action.parameters)
            elif action.action_type == "select_option":
                self._select_option(action.parameters)
            elif action.action_type == "check_checkbox":
                self._check_checkbox(action.parameters)
            elif action.action_type == "click_button":
                self._click_button(action.parameters)
            elif action.action_type == "wait":
                self._wait(action.parameters)
            elif action.action_type == "navigate":
                self._navigate(action.parameters)

            print(f"✓ Executed: {action.action_type} - {action.reasoning}")

            self.action_history.append(action)

            time.sleep(0.5)

        except Exception as e:
            print(f"✗ Failed to execute {action.action_type}: {e}")
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

    def run(self, url: str, user_id: str):
        try:
            # Initial page load
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            print("Page loaded successfully")

            max_iterations = 20
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                print(f"\n--- Iteration {iteration} ---")

                html_content = self.driver.page_source
                self.website_status = self.analyze_form_html(html_content)

                decision = self.make_decision(self.website_status)
                print(f"Decision: {decision.status}")
                print(f"Message: {decision.message}")

                if decision.status == "complete":
                    print("Form completed")
                    self.status = "completed"
                    break

                if decision.action:
                    self.execute_action(decision)
                    self.status = "updated"
                else:
                    print("No action returned but status is not complete")
                    break

                time.sleep(1)

            if iteration >= max_iterations:
                print("Max iterations reached - stopping to prevent infinite loop")
                self.status = "error"

        except Exception as e:
            print(f"Error in browser automation: {e}")
            self.status = "error"

    def start(self, request):
        print(f"Starting browser launch thread for URL: {request.url}")
        thread = threading.Thread(target=self.run, args=(request.url, request.user_id))
        thread.start()
