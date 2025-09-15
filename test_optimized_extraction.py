#!/usr/bin/env python3
"""
Test the optimized recommendation extraction with the sample final_analysis text.
"""

import re

def optimized_extract_recommendation(final_analysis: str) -> str:
    """Extract BUY/SELL/HOLD recommendation with optimized precision focusing on summary section."""
    if not final_analysis:
        return 'HOLD'
    
    analysis_upper = final_analysis.upper()
    
    # PRIORITY 1: Look for "In summary" section (highest priority)
    summary_patterns = [
        r'\*\*IN\s+SUMMARY:\*\*\s*\*\*(\w+)\*\*',        # **In summary:** **HOLD**
        r'\*\*IN\s+SUMMARY[:\s]*\*\*\s*\*\*(\w+)\*\*',   # **In summary:** **HOLD** (flexible spacing)
        r'\*\*IN\s+SUMMARY[:\s]*\*\*[^*]*\*\*(\w+)\*\*', # **In summary:** ... **HOLD** (with text between)
        r'IN\s+SUMMARY[:\s]*\*\*(\w+)\*\*',              # In summary: **HOLD** (without bold summary)
        r'SUMMARY[:\s]*\*\*(\w+)\*\*',                   # Summary: **HOLD**
    ]
    
    print("🔍 Testing PRIORITY 1: In summary section...")
    for pattern in summary_patterns:
        matches = re.findall(pattern, analysis_upper)
        print(f"   Pattern: {pattern}")
        print(f"   Matches: {matches}")
        for match in matches:
            if match in ['BUY', 'SELL', 'HOLD']:
                print(f"   ✅ Found in summary: {match}")
                return match
    
    # PRIORITY 2: Look for explicit recommendation statements in the last portion
    last_section = analysis_upper[-500:] if len(analysis_upper) > 500 else analysis_upper
    
    print("🔍 Testing PRIORITY 2: Last section patterns...")
    final_recommendation_patterns = [
        r'MY\s+RECOMMENDATION\s+IS\s+TO\s+(\w+)',
        r'RECOMMENDATION\s+IS\s+TO\s+(\w+)',
        r'RECOMMEND\s+(\w+)',
        r'FINAL\s+RECOMMENDATION[:\s]*(\w+)',
        r'CONCLUSION[:\s]*(\w+)',
    ]
    
    for pattern in final_recommendation_patterns:
        matches = re.findall(pattern, last_section)
        print(f"   Pattern: {pattern}")
        print(f"   Matches: {matches}")
        for match in matches:
            if match in ['BUY', 'SELL', 'HOLD']:
                print(f"   ✅ Found in last section: {match}")
                return match
    
    # PRIORITY 3: Look for bolded recommendations in the last section
    print("🔍 Testing PRIORITY 3: Bolded recommendations in last section...")
    bolded_matches = re.findall(r'\*\*(\w+)\*\*', last_section)
    print(f"   Bolded matches: {bolded_matches}")
    for match in bolded_matches:
        if match in ['BUY', 'SELL', 'HOLD']:
            print(f"   ✅ Found bolded: {match}")
            return match
    
    print("🔍 No high-priority matches found, using fallback logic...")
    return 'HOLD'

def main():
    """Test the optimized extraction with sample text."""
    
    # Sample text from the user
    sample_text = """Based on the comprehensive debate and the guiding principles for risk management, my recommendation is to **Hold** at this stage.

**Rationale:**

- The **Risky Analyst** highlights Snap's potential for innovation-driven rebound, emphasizing the possibility of capturing upside if new features succeed and market sentiment shifts favorably. However, this perspective relies heavily on optimistic assumptions and ignores the significant operational and competitive headwinds, along with technical warning signs indicating downward momentum.
- The **Safe/Conservative Analyst** raises valid concerns about Snap's declining user engagement, legal challenges, and overall bearish technical signals. The cautious approach favors capital preservation but could be overly conservative, potentially missing out on opportunities if the company demonstrates early signs of recovery.
- The **Neutral Analyst** advocates for a balanced approach, recognizing both risks and opportunities. They suggest a phased strategy—trimming positions rather than full exit or full commitment—allowing for flexibility and adaptation as new information becomes available.

**Key technical and fundamental considerations:**

- Technical signals (below key moving averages, negative MACD, RSI near neutral but with downward bias) suggest momentum remains bearish.
- Operational challenges, market saturation, increased competition, and legal risks create significant downside vulnerabilities.
- Macro tailwinds (e.g., lower interest rates) could support ad spend and growth, but these effects are uncertain and may take time to manifest.

**Actionable plan:**

- Implement a phased approach:
- **Do not buy aggressively**; avoid increased exposure given the current risks.
- **Hold existing positions** without ramping up investment until clearer signs of stabilization emerge.
- Use **stop-loss orders** just below recent support levels to manage downside risk.
- Monitor for early signs of turnaround:
- Improved user engagement metrics
- Positive technical divergence
- Overcome legal hurdles
- Signals of market sentiment turning bullish

- Be prepared to **reassess and re-enter** or **reduce further** based on evolving company fundamentals and technical developments.

**Lesson from past reflections:**

- Avoid overreliance on optimistic assumptions; prioritize risk signals.
- Use flexible, phased strategies to adapt to new information.
- Maintain discipline by not rushing into a buy or full sell unless strongly supported by clear indicators.

**In summary:** **Hold**—this decision balances current technical and fundamental risks with potential upside opportunities, favoring risk management and flexibility over hasty actions. It positions us to act decisively if positive signs emerge, while avoiding the pitfalls of overcommitment in a volatile environment."""

    print("🧪 Testing Optimized Recommendation Extraction")
    print("=" * 80)
    
    result = optimized_extract_recommendation(sample_text)
    
    print("=" * 80)
    print(f"🎯 FINAL RESULT: {result}")
    
    # Verify it matches the expected result
    if result == "HOLD":
        print("✅ SUCCESS: Correctly extracted HOLD from 'In summary' section")
    else:
        print(f"❌ FAILED: Expected HOLD but got {result}")
    
    # Show the key section that should be matched
    print("\n📋 Key section that should be matched:")
    print("**In summary:** **Hold**—this decision balances...")
    
    return result

if __name__ == "__main__":
    main()