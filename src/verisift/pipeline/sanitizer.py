import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ExclusionManager:
    """
    Manages the detection and highlighting of dynamic patterns (dates, IDs) 
    that should be ignored during the comparison process.
    """
    def __init__(self, patterns: List[str], enabled: bool):
        self.patterns = patterns
        self.enabled = enabled
        self.match_history: List[Dict[str, str]] = []

    def sanitize_text(self, text: str) -> tuple[bool, str]:
        """
        Scans text for regex patterns. Matches are wrapped in an amber span 
        so the diff engine treats them as 'equal' but the report highlights them.
        """
        if not self.enabled:
            logger.warning(f"exclusions disabled!!! text exclusions skipped")
            return False, text

        if not self.patterns:
            logger.warning(f"no exclusion patterns found!!! text exclusions skipped: (exclusion patterns = {self.patterns})")
            return False, text


        sanitized_text = text
        
        try:
            
            for pattern in self.patterns:
                try:
                    # Find matches to record in the log before we modify the string
                    matches = re.findall(pattern, sanitized_text)
                    
                    if matches:
                        for match in matches:
                            # Handle potential group tuples from findall
                            match_str = match if isinstance(match, str) else match[0]
                            
                            self.match_history.append({
                                "text": match_str,
                                "pattern": pattern
                            })
                            logger.info(f"Exclusion Applied: '{match_str}' matched by r'{pattern}'")

                        # Wrap matches in a span. 
                        # We use a lambda to ensure we don't trip over backslashes in the matched text.
                        sanitized_text = re.sub(
                            pattern,
                            lambda m: f'<span class="diff_excluded">{m.group(0)}</span>',
                            sanitized_text
                        )
                except re.error as e:
                    logger.error(f"Invalid Regex Pattern '{pattern}': {e}")
                    continue

            return True, sanitized_text
        
        except Exception as e:
            logger.warning(f"Error while applying exclusions to text: {e}")
            return False, text


    def get_debug_summary(self) -> List[Dict[str, str]]:
        """Returns a list of all items captured by the exclusion engine."""
        return self.match_history

    def clear_history(self):
        """Clears logs between different page/document runs."""
        self.match_history = []


