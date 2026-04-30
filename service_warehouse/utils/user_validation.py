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


def user_validation(doc, method=None):
    if doc.doctype != "User":
        return

    previous_doc = doc.get_doc_before_save()
    if previous_doc and doc.get("username") != previous_doc.get("username"):
        frappe.throw("Username cannot be changed")

    if doc.is_new():
        doc.send_welcome_email = 0

    _sanitize_turkish_chars(doc)
