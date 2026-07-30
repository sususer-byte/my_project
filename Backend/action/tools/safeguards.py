#Safeguards for tool parameter validation.

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("furgal.action.tools")

DANGEROUS_PATTERNS = [
    r"rm\s+-rf",
    r"rm\s+-r\s+/",
    r"format\s+[a-z]:",
    r"mkfs\.",
    r"dd\s+if=",
    r":\(\)\{",
    r"shutdown\s+-",
    r"restart-computer",
    r"stop-computer",
    r"del\s+/[fq]",
    r"rmdir\s+/s",
    r"powershell.*-enc",
    r"invoke-expression",
    r"iex\s*\(",
    r"start-process\s+.*-verb\s+runas",
    r"reg\s+delete",
    r"takeown\s+/f",
    r"icacls\s+.*\s/grant",
    r"wget\s+.*\|\s*sh",
    r"curl\s+.*\|\s*bash",
]

DANGEROUS_RE = re.compile("|".join(DANGEROUS_PATTERNS), re.IGNORECASE)


def contains_dangerous_command(value: str) -> bool:
    if not value:
        return False
    return bool(DANGEROUS_RE.search(value))


def scan_value_for_danger(value: Any) -> Optional[str]:
    #Recursively scan a value for dangerous command strings.
    if isinstance(value, str):
        if contains_dangerous_command(value):
            return f"Dangerous command pattern detected: {value[:80]}"
        return None
    if isinstance(value, dict):
        for nested in value.values():
            hit = scan_value_for_danger(nested)
            if hit:
                return hit
        return None
    if isinstance(value, list):
        for nested in value:
            hit = scan_value_for_danger(nested)
            if hit:
                return hit
        return None
    return None


def validate_safe_args(args: Dict[str, Any]) -> Optional[str]:
    #Return error message if args contain dangerous content, else None.
    if not isinstance(args, dict):
        return "Tool arguments must be a dictionary"
    return scan_value_for_danger(args)
