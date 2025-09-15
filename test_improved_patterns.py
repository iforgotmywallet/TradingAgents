#!/usr/bin/env python3
"""
Test improved patterns for the "In summary" section.
"""

import re

def test_patterns():
    """Test different regex patterns against the sample text."""
    
    # The actual text from the sample
    sample_text = "**In summary:** **Hold**—this decision balances current technical and fundamental risks"
    
    print("🧪 Testing patterns against:")
    print(f"'{sample_text}'")
    print("=" * 80)
    
    patterns = [
        r'IN\s+SUMMARY[:\s]*\*\*(\w+)\*\*',           # Original
        r'\*\*IN\s+SUMMARY[:\s]*\*\*\s*\*\*(\w+)\*\*', # Bolded "In summary"
        r'\*\*IN\s+SUMMARY[:\s]*\*\*[^*]*\*\*(\w+)\*\*', # More flexible
        r'IN\s+SUMMARY[:\s]*(\w+)(?:\s|—)',            # Without bold requirement
        r'\*\*IN\s+SUMMARY:\*\*\s*\*\*(\w+)\*\*',      # Specific colon format
        r'SUMMARY[:\s]*\*\*(\w+)\*\*',                 # Just "summary"
    ]
    
    text_upper = sample_text.upper()
    
    for i, pattern in enumerate(patterns, 1):
        print(f"Pattern {i}: {pattern}")
        matches = re.findall(pattern, text_upper)
        print(f"Matches: {matches}")
        if matches and matches[0] in ['BUY', 'SELL', 'HOLD']:
            print(f"✅ SUCCESS: Found {matches[0]}")
        else:
            print("❌ No valid match")
        print()
    
    # Let's also test a simpler approach - look for the pattern in the text
    print("🔍 Manual inspection:")
    print(f"Text contains '**IN SUMMARY:**': {'**IN SUMMARY:**' in text_upper}")
    print(f"Text contains '**HOLD**': {'**HOLD**' in text_upper}")
    
    # Try a more direct approach
    if '**IN SUMMARY:**' in text_upper and '**HOLD**' in text_upper:
        # Find the position of "In summary" and look for the next bolded word
        summary_pos = text_upper.find('**IN SUMMARY:**')
        if summary_pos != -1:
            # Look for the next **WORD** after the summary
            after_summary = text_upper[summary_pos:]
            bolded_pattern = r'\*\*(\w+)\*\*'
            matches = re.findall(bolded_pattern, after_summary)
            print(f"Bolded words after 'In summary': {matches}")
            for match in matches:
                if match in ['BUY', 'SELL', 'HOLD']:
                    print(f"✅ DIRECT APPROACH SUCCESS: {match}")
                    break

if __name__ == "__main__":
    test_patterns()