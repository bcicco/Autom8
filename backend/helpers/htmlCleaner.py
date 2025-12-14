from bs4 import BeautifulSoup, NavigableString, Comment


def clean_html_for_llm(html_content: str) -> str:
    """
    Clean HTML by removing hidden elements, scripts, styles, and other non-essential content.
    Returns a simplified HTML string suitable for LLM processing.

    Removes:
    - Scripts, styles, and non-content tags
    - Hidden elements (hidden attribute, display:none, visibility:hidden)
    - Navigation and header/footer content (configurable)
    - All styling attributes
    - Event handlers and accessibility attributes
    - Comments
    - Excessive whitespace

    Preserves:
    - All form elements (input, select, textarea, button with type=submit)
    - Form structure and labels
    - Essential attributes (id, name, value, type, required, placeholder)
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script, style, and other non-content tags
    for tag in soup(["script", "style", "link", "meta", "noscript", "svg", "img"]):
        tag.decompose()

    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove navigation, header, and footer (usually not relevant for form filling)
    for tag in soup.find_all(["nav", "header", "footer"]):
        tag.decompose()

    # Remove elements with role="navigation" or role="banner"
    for tag in soup.find_all(attrs={"role": ["navigation", "banner", "contentinfo"]}):
        tag.decompose()

    # Remove hidden elements - need to check if tag has attrs before accessing
    tags_to_remove = []
    for tag in soup.find_all(True):
        # Skip if not a tag element
        if not hasattr(tag, "name") or isinstance(tag, NavigableString):
            continue

        # Skip if attrs is None
        if not hasattr(tag, "attrs") or tag.attrs is None:
            continue

        # Check for hidden attribute
        if "hidden" in tag.attrs:
            tags_to_remove.append(tag)
            continue

        # Check aria-hidden
        if tag.attrs.get("aria-hidden") == "true":
            tags_to_remove.append(tag)
            continue

        # Check aria-expanded (collapsed menus/accordions)
        if tag.attrs.get("aria-expanded") == "false":
            tags_to_remove.append(tag)
            continue

        # Check inline styles for hidden elements
        style = tag.attrs.get("style", "")
        if style:
            style_lower = style.lower()
            if any(
                prop in style_lower
                for prop in [
                    "display:none",
                    "display: none",
                    "visibility:hidden",
                    "visibility: hidden",
                ]
            ):
                tags_to_remove.append(tag)
                continue

        # Check class names that commonly indicate hidden elements
        classes = tag.attrs.get("class", [])
        if isinstance(classes, list) and any(
            cls in ["hidden", "d-none", "hide", "invisible", "collapse", "collapsed"]
            for cls in classes
        ):
            tags_to_remove.append(tag)
            continue

    # Remove all collected hidden elements
    for tag in tags_to_remove:
        tag.decompose()

    # Clean up remaining elements - remove unnecessary attributes
    for tag in soup.find_all(True):
        if not hasattr(tag, "attrs") or tag.attrs is None:
            continue

        # Keep only essential attributes based on tag type
        if tag.name in ["input", "select", "textarea", "button"]:
            # For form elements, keep important attributes
            attrs_to_keep = [
                "id",
                "name",
                "type",
                "value",
                "placeholder",
                "required",
                "checked",
                "selected",
                "disabled",
            ]
            attrs_to_remove = [
                attr for attr in list(tag.attrs.keys()) if attr not in attrs_to_keep
            ]
        elif tag.name in ["label", "form"]:
            # For labels and forms, keep minimal attributes
            attrs_to_keep = ["id", "for", "action", "method"]
            attrs_to_remove = [
                attr for attr in list(tag.attrs.keys()) if attr not in attrs_to_keep
            ]
        else:
            # For other elements, remove most attributes
            attrs_to_keep = ["id"]
            attrs_to_remove = [
                attr for attr in list(tag.attrs.keys()) if attr not in attrs_to_keep
            ]

        # Remove the attributes
        for attr in attrs_to_remove:
            del tag.attrs[attr]

    # Get cleaned HTML
    cleaned_html = str(soup)

    # Remove extra whitespace while preserving structure
    lines = []
    for line in cleaned_html.split("\n"):
        stripped = line.strip()
        if stripped:
            lines.append(stripped)

    cleaned_html = "\n".join(lines)

    return cleaned_html
