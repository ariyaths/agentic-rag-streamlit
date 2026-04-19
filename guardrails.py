import re

# Maintain lists of banned keywords
INPUT_BANNED_KEYWORDS = ["confidential", "ssh", "key", "API", "password", "env", "secret", "classified", "restricted", "internal use"]
OUTPUT_BANNED_KEYWORDS = ["confidential", "ssh", "key", "API", "env", "password", "classified", "restricted", "internal use"]

def check_guardrails(text: str, is_input: bool = True) -> tuple[bool, str]:
    """
    Checks if text contains banned keywords.
    Returns (True, "") if SAFE, (False, keyword) if UNSAFE.
    """
    if not text:
        return True, ""
    
    keywords = INPUT_BANNED_KEYWORDS if is_input else OUTPUT_BANNED_KEYWORDS
    for keyword in keywords:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            return False, keyword
    return True, ""

def get_guardrail_message(keyword: str = "") -> str:
    if keyword:
        return f"🛑 Output generation stopped due to policy violation (guardrail triggered by '{keyword}')."
    return "🛑 Output generation stopped due to policy violation (guardrail triggered)."