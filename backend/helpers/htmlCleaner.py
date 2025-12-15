from bs4 import BeautifulSoup, Comment


def clean_html_for_llm(html_content: str) -> str:
    """
    Clean HTML by removing hidden elements, scripts, styles, and other non-essential content.
    Returns a simplified HTML string suitable for LLM processing.

    Removes:
    - Scripts, styles, metadata, and non-content tags
    - Hidden elements (display:none, visibility:hidden, aria-hidden, etc.)
    - Navigation, headers, and footers
    - Styling, event handlers, and non-essential attributes
    - HTML comments and excessive whitespace

    Preserves:
    - Form elements (input, select, textarea, button)
    - Form structure and labels
    - Essential attributes (id, name, value, type, required, placeholder, etc.)
    - Main content structure

    Args:
        html_content: Raw HTML string to clean

    Returns:
        Cleaned HTML string optimized for LLM processing
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Step 1: Remove non-content tags (scripts, styles, metadata)
    NON_CONTENT_TAGS = [
        "script",
        "style",
        "link",
        "meta",
        "noscript",
        "svg",
        "img",
        "head",
        "iframe",
        "object",
        "embed",
    ]
    for tag in soup(NON_CONTENT_TAGS):
        tag.decompose()

    # Step 2: Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Step 3: Remove navigation and structural chrome
    STRUCTURAL_TAGS = ["nav", "header", "footer", "aside"]
    for tag in soup(STRUCTURAL_TAGS):
        tag.decompose()

    # Step 4: Remove elements by role
    UNWANTED_ROLES = ["navigation", "banner", "contentinfo", "complementary", "search"]
    for tag in soup.find_all(attrs={"role": UNWANTED_ROLES}):
        tag.decompose()

    # Step 5: Remove hidden elements (collect first to avoid modification during iteration)
    HIDDEN_CLASSES = {
        "hidden",
        "d-none",
        "hide",
        "invisible",
        "collapse",
        "collapsed",
        "sr-only",
    }
    HIDDEN_STYLE_PATTERNS = [
        "display:none",
        "display: none",
        "visibility:hidden",
        "visibility: hidden",
    ]

    tags_to_remove = []

    for tag in soup.find_all(True):
        if not hasattr(tag, "attrs") or tag.attrs is None:
            continue

        # Check hidden attribute
        if tag.has_attr("hidden"):
            tags_to_remove.append(tag)
            continue

        # Check aria-hidden
        if tag.get("aria-hidden") == "true":
            tags_to_remove.append(tag)
            continue

        # Check aria-expanded (collapsed menus/accordions) - remove the CONTENT containers
        if tag.get("aria-expanded") == "false":
            tags_to_remove.append(tag)
            continue

        # Check inline styles for hidden elements
        style = tag.get("style", "")
        if style and any(pattern in style.lower() for pattern in HIDDEN_STYLE_PATTERNS):
            tags_to_remove.append(tag)
            continue

        # Check class names for hidden indicators
        classes = tag.get("class", [])
        if isinstance(classes, list) and HIDDEN_CLASSES & set(classes):
            tags_to_remove.append(tag)
            continue

    # Remove all hidden elements
    for tag in tags_to_remove:
        tag.decompose()

    # Step 6: Clean attributes from remaining elements
    FORM_ELEMENT_ATTRS = {
        "id",
        "name",
        "type",
        "value",
        "placeholder",
        "required",
        "checked",
        "selected",
        "disabled",
        "readonly",
        "min",
        "max",
        "step",
        "pattern",
        "maxlength",
    }
    LABEL_FORM_ATTRS = {"id", "for", "action", "method", "enctype"}
    MINIMAL_ATTRS = {"id", "href", "title"}

    for tag in soup.find_all(True):
        if not hasattr(tag, "attrs") or not tag.attrs:
            continue

        # Determine which attributes to keep based on tag type
        if tag.name in ["input", "select", "textarea", "button"]:
            attrs_to_keep = FORM_ELEMENT_ATTRS
        elif tag.name in ["label", "form"]:
            attrs_to_keep = LABEL_FORM_ATTRS
        elif tag.name == "a":
            attrs_to_keep = MINIMAL_ATTRS
        else:
            attrs_to_keep = {"id"}

        # Remove unwanted attributes
        attrs_to_remove = [
            attr for attr in list(tag.attrs.keys()) if attr not in attrs_to_keep
        ]
        for attr in attrs_to_remove:
            del tag.attrs[attr]

    # Step 7: Remove empty elements (except form inputs and self-closing tags)
    PRESERVE_EMPTY_TAGS = {"input", "textarea", "select", "button", "br", "hr"}

    # Repeat until no more empty elements are found
    changed = True
    while changed:
        changed = False
        for tag in soup.find_all(True):
            # Skip tags that are allowed to be empty
            if tag.name in PRESERVE_EMPTY_TAGS:
                continue

            # Check if tag is effectively empty (no text and no meaningful children)
            if not tag.get_text(strip=True):
                # Check if it has any non-empty children
                has_meaningful_children = any(
                    child.name in PRESERVE_EMPTY_TAGS for child in tag.find_all(True)
                )

                if not has_meaningful_children:
                    tag.decompose()
                    changed = True

    # Step 8: Unwrap redundant nested spans and divs
    for tag in soup.find_all(["span", "div"]):
        # If a span/div only contains another span/div with no attributes, unwrap it
        children = list(tag.children)
        if len(children) == 1 and hasattr(children[0], "name"):
            child = children[0]
            if child.name in ["span", "div"] and not tag.attrs:
                tag.unwrap()

    # Step 9: Convert to string and clean whitespace
    cleaned_html = str(soup)

    # Remove excessive whitespace while preserving structure
    lines = [line.strip() for line in cleaned_html.split("\n") if line.strip()]
    cleaned_html = "\n".join(lines)

    return cleaned_html
