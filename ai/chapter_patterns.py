"""
Shared Chapter Detection Patterns
Centralized patterns for various book formats
"""

import re
from typing import Dict, List


CHAPTER_PATTERNS: Dict[str, List[str]] = {
    'standard': [
        r'^CHAPTER\s+[IVX\d]+\.?\s*$',
        r'^Chapter\s+[IVX\d]+\.?\s*$',
        r'^Chapter\s+[IVX\d]+\.?\s+.*$',
    ],
    'roman_numerals': [
        r'^[IVX]+\.?\s*$',
        r'^[IVX]+\.?\s+.*$',
    ],
    'arabic_numerals': [
        r'^\d+\.?\s*$',
        r'^\d+\.?\s+.*$',
    ],
    'descriptive': [
        r'^[A-Z][A-Z\s]+$',  # ALL CAPS titles
        r'^[A-Z][a-z\s]+$',  # Title Case
    ],
    'special_formats': [
        r'^Book\s+[IVX\d]+',  # Book I, Book 1, etc.
        r'^Part\s+[IVX\d]+',  # Part I, Part 1, etc.
        r'^Section\s+[IVX\d]+',  # Section I, etc.
    ]
}


def match_pattern(text: str) -> tuple:
    """
    Check if text matches any chapter pattern
    
    Returns:
        (matched, pattern_type, confidence) tuple
    """
    text = text.strip()
    
    for pattern_type, patterns in CHAPTER_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, text, re.IGNORECASE):
                confidence = _calculate_confidence(pattern, text)
                return (True, pattern_type, confidence)
    
    return (False, None, 0.0)


def _calculate_confidence(pattern: str, text: str) -> float:
    """Calculate confidence score for pattern matches"""
    base_confidence = 0.8
    
    # Boost confidence for more specific patterns
    if 'CHAPTER' in pattern.upper():
        base_confidence += 0.1
    if r'\d+' in pattern:  # Contains numbers
        base_confidence += 0.05
    if len(text.strip()) < 50:  # Short, likely heading
        base_confidence += 0.05
    
    return min(base_confidence, 1.0)


def get_all_patterns() -> List[str]:
    """Get flattened list of all patterns"""
    patterns = []
    for pattern_list in CHAPTER_PATTERNS.values():
        patterns.extend(pattern_list)
    return patterns

