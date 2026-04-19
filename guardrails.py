import re

# Maintain a list of banned keywords
BANNED_KEYWORDS = ["confidential", "ssh", "key", "env", "secret", "classified", "restricted", "internal use"]

def check_guardrails(text: str) -> bool:
    """
    Checks if text contains banned keywords.
    Returns True if SAFE, False if UNSAFE.
    """
    if not text:
        return True
    
    text_lower = text.lower()
    for keyword in BANNED_KEYWORDS:
        if keyword in text_lower:
            return False
    return True

def get_guardrail_message() -> str:
    return "🛑 Output generation stopped due to policy violation (guardrail triggered)."