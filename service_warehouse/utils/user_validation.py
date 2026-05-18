import frappe

TURKISH_CHARS = "çğıİöşüÇĞÖŞÜ"

TURKISH_MAP = {
    "ç": "c", "Ç": "C",
    "ğ": "g", "Ğ": "G",
    "ı": "i", "İ": "I",
    "ö": "o", "Ö": "O",
    "ş": "s", "Ş": "S",
    "ü": "u", "Ü": "U",
}

FIELDS_TO_CHECK = [
    "email",
    "username",
]


def _replace_turkish(s: str) -> str:
    return "".join(TURKISH_MAP.get(ch, ch) for ch in s)


def _sanitize_turkish_chars(doc):
    """Replace Turkish characters in configured fields (preserve case mapping)"""
    for field in FIELDS_TO_CHECK:
        value = doc.get(field)
        if isinstance(value, str) and any(ch in value for ch in TURKISH_CHARS):
            new_value = _replace_turkish(value)
            setattr(doc, field, new_value)


def _generate_fallback_username(doc) -> str:
    """first_name_sanitized + _ + email local part (both Turkish-cleaned)"""
    first = frappe.scrub(_replace_turkish(doc.first_name or ""))
    local = _replace_turkish((doc.email or "").split("@")[0])
    return f"{first}_{local}"


def user_validation(doc, method=None):
    if doc.doctype != "User":
        return

    if doc.is_new():
        doc.send_welcome_email = 0
        _sanitize_turkish_chars(doc)
        # Frappe clears username when it finds a conflict; apply fallback in that case
        if not doc.username:
            doc.username = _generate_fallback_username(doc)
        return

    # For existing users: block genuine username changes but allow sanitization
    previous_doc = doc.get_doc_before_save()
    if previous_doc:
        prev_username = _replace_turkish(previous_doc.get("username") or "")
        curr_username = _replace_turkish(doc.get("username") or "")
        if prev_username != curr_username:
            frappe.throw("Username cannot be changed")

    _sanitize_turkish_chars(doc)
