"""Lightweight PII detection for privacy compliance"""

import re
from typing import Dict, List, Optional


class PIIDetector:
    """Detect potential PII in text content"""
    
    # Regex patterns for common PII
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b',
        'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'person_name': None,  # Requires NER or name list
        'address': None,  # Complex, requires geocoding or patterns
        'id_number': r'\b[A-Z]{1,2}\d{6,10}\b',  # Generic ID pattern
    }
    
    # Common false positives to exclude
    FALSE_POSITIVES = {
        'ip_address': ['127.0.0.1', '0.0.0.0', '192.168.', '10.0.', '172.16.'],
        'phone': ['123-456-7890', '000-000-0000', '111-111-1111'],
        'credit_card': ['0000-0000-0000-0000', '1234-5678-9012-3456'],
    }
    
    @classmethod
    def detect_pii(cls, text: str) -> Dict[str, bool]:
        """
        Detect potential PII in text
        
        Args:
            text: Text to scan for PII
            
        Returns:
            Dictionary of PII types and whether they were detected
        """
        pii_flags = {
            "email": False,
            "phone": False,
            "ssn": False,
            "credit_card": False,
            "ip_address": False,
            "person_name": False,
            "address": False,
            "id_number": False,
        }
        
        if not text:
            return pii_flags
        
        # Check each pattern
        for pii_type, pattern in cls.PATTERNS.items():
            if pattern is None:
                continue
                
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            if matches:
                # Filter out known false positives
                if pii_type in cls.FALSE_POSITIVES:
                    filtered_matches = [
                        m for m in matches 
                        if not any(fp in str(m) for fp in cls.FALSE_POSITIVES[pii_type])
                    ]
                    if filtered_matches:
                        pii_flags[pii_type] = True
                else:
                    pii_flags[pii_type] = True
        
        # Basic name detection (looks for Title Case patterns)
        name_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b'
        potential_names = re.findall(name_pattern, text)
        
        # Filter out common non-names
        non_names = ['The Internet', 'New York', 'United States', 'Web Services', 
                     'Machine Learning', 'Artificial Intelligence', 'User Guide']
        
        filtered_names = [
            name for name in potential_names 
            if name not in non_names and len(name.split()) >= 2
        ]
        
        if len(filtered_names) > 2:  # Multiple names suggest PII
            pii_flags['person_name'] = True
        
        # Basic address detection (number + street pattern)
        address_pattern = r'\b\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Place|Pl)\b'
        if re.search(address_pattern, text, re.IGNORECASE):
            pii_flags['address'] = True
        
        return pii_flags
    
    @classmethod
    def redact_pii(cls, text: str, pii_flags: Optional[Dict[str, bool]] = None) -> str:
        """
        Redact detected PII from text
        
        Args:
            text: Text containing PII
            pii_flags: Pre-detected PII flags, or None to detect
            
        Returns:
            Text with PII redacted
        """
        if pii_flags is None:
            pii_flags = cls.detect_pii(text)
        
        redacted = text
        
        for pii_type, detected in pii_flags.items():
            if not detected or pii_type not in cls.PATTERNS:
                continue
            
            pattern = cls.PATTERNS[pii_type]
            if pattern:
                if pii_type == 'email':
                    redacted = re.sub(pattern, '[EMAIL_REDACTED]', redacted, flags=re.IGNORECASE)
                elif pii_type == 'phone':
                    redacted = re.sub(pattern, '[PHONE_REDACTED]', redacted)
                elif pii_type == 'ssn':
                    redacted = re.sub(pattern, '[SSN_REDACTED]', redacted)
                elif pii_type == 'credit_card':
                    redacted = re.sub(pattern, '[CC_REDACTED]', redacted)
                elif pii_type == 'ip_address':
                    # Don't redact common local IPs
                    for match in re.finditer(pattern, redacted):
                        ip = match.group()
                        if not any(fp in ip for fp in cls.FALSE_POSITIVES.get('ip_address', [])):
                            redacted = redacted.replace(ip, '[IP_REDACTED]')
        
        return redacted
    
    @classmethod
    def get_pii_summary(cls, pii_flags: Dict[str, bool]) -> str:
        """
        Get human-readable summary of detected PII
        
        Args:
            pii_flags: Dictionary of PII detection results
            
        Returns:
            Summary string
        """
        detected = [pii_type for pii_type, found in pii_flags.items() if found]
        
        if not detected:
            return "No PII detected"
        
        return f"PII detected: {', '.join(detected)}"