def generate_system_prompt_html(html_content: str) -> list:
    """
    returns a formatted string, essentially the system prompt

    Returns:
        str: A formatted string suitable for HTML analyses.
    """
    return [
        {
            "role": "system",
            "content": """You are an expert at analyzing webpages, especially HTML forms. Extract all form fields with their properties AND all clickable buttons on the page.

IMPORTANT: 
- Look for the 'value' attribute in form fields to capture pre-filled values.
- Detect ALL buttons including: submit buttons, regular buttons, close buttons (X), modal dismiss buttons, navigation buttons, etc.
- For buttons, capture their text content, CSS selectors, type, and any identifying attributes.
- CRITICAL: Keep your response concise. Only extract the ESSENTIAL form fields and buttons. Don't include every single element if there are many.
- Prioritize: visible input fields, submit buttons, navigation buttons, and form controls the user needs to interact with.
- For dropdowns with options, provide up to five examples of real possible selections

Return your response as a JSON object in this exact format (no markdown, no explanation):
{
    "fields": [
        {
            "name": "field_name",
            "type": "text",
            "label": "Field Label",
            "option_description": [
                "example1",
                "example2",
                "example3",
                "example4",
                "example5"
            ],

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
    ]


def generate_system_prompt_decision(form_info: str, history_str: str) -> str:
    return [
        {
            "role": "system",
            "content": """You are an intelligent form-filling assistant. Analyze the webpage and decide what SEQUENCE of actions to take to complete it.

Available user data:
- username: "ben.cicco@yahoo.com"
- password: "Ben10%123098765"
- visa type: "student"
- country: "Equador"


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
10. Option_description provides only examples of the possible options, not the complete set of options. It is included to help you understand how the value should be formatted (e.g caps, abbrievations)
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
    ]
