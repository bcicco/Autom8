from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any


class FormField(BaseModel):
    name: str
    type: str
    label: Optional[str] = None
    option_description: Optional[List[str]] = None
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
    button_type: str
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
