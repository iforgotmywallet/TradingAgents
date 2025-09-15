#!/usr/bin/env python3
"""
Fix SNAP recommendation extraction issue.

The current logic incorrectly extracts SELL when the analysis clearly states HOLD.
This script implements a more precise extraction logic.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

def improved_extract_recommendation(final_analysis: str) -> str:
    """
    Improved recommendation extraction that looks for explicit recommendations first.
    """
    if not final_analysis:
        return 'HOLD'
    
    analysis_upper = final_analysis.upper()
    
    # Look for explicit recommendation statements first (more precise)
    recommendation_patterns = [
        # Look for "recommendation is to X" or "recommend X"
        r'RECOMMENDATION\s+IS\s+TO\s+(\w+)',
        r'RECOMMEND\s+(\w+)',
        r'MY\s+RECOMMENDATION\s+IS\s+(\w+)',
        # Look for bolded recommendations
        r'\*\*(\w+)\*\*',
        # Look for final summary statements
        r'IN\s+SUMMARY[:\s]*\*\*(\w+)\*\*',
        r'FINAL\s+RECOMMENDATION[:\s]*(\w+)',
    ]
    
    import re
    
    # First, try to find explicit recommendation patterns
    for pattern in recommendation_patterns:
        matches = re.findall(pattern, analysis_upper)
        for match in matches:
            if match in ['BUY', 'SELL', 'HOLD']:
                print(f"Found explicit recommendation: {match}")
                return match
    
    # If no explicit pattern found, look for the most prominent recommendation
    # Count occurrences of each recommendation in context
    buy_contexts = len(re.findall(r'(?:RECOMMEND|SUGGESTION|DECISION).*?BUY', analysis_upper))
    sell_contexts = len(re.findall(r'(?:RECOMMEND|SUGGESTION|DECISION).*?SELL', analysis_upper))
    hold_contexts = len(re.findall(r'(?:RECOMMEND|SUGGESTION|DECISION).*?HOLD', analysis_upper))
    
    print(f"Contextual recommendations - BUY: {buy_contexts}, SELL: {sell_contexts}, HOLD: {hold_contexts}")
    
    # Return the most contextually relevant recommendation
    if hold_contexts > max(buy_contexts, sell_contexts):
        return 'HOLD'
    elif buy_contexts > sell_contexts:
        return 'BUY'
    elif sell_contexts > buy_contexts:
        return 'SELL'
    
    # Fallback to simple word counting (but be more careful)
    # Only count if they appear as standalone recommendations
    buy_count = len(re.findall(r'\bBUY\b', analysis_upper))
    sell_count = len(re.findall(r'\bSELL\b', analysis_upper))
    hold_count = len(re.findall(r'\bHOLD\b', analysis_upper))
    
    print(f"Word counts - BUY: {buy_count}, SELL: {sell_count}, HOLD: {hold_count}")
    
    # Look for sentiment indicators only if no clear recommendation
    if max(buy_count, sell_count, hold_count) == 0:
        positive_indicators = ["BULLISH", "POSITIVE", "UPWARD", "LONG", "INVEST", "PURCHASE"]
        negative_indicators = ["BEARISH", "NEGATIVE", "DOWNWARD", "SHORT", "AVOID", "DECLINE"]
        
        positive_count = sum(1 for indicator in positive_indicators if indicator in analysis_upper)
        negative_count = sum(1 for indicator in negative_indicators if indicator in analysis_upper)
        
        if positive_count > negative_count:
            return 'BUY'
        elif negative_count > positive_count:
            return 'SELL'
    
    # Return the most frequent explicit recommendation
    if hold_count >= max(buy_count, sell_count):
        return 'HOLD'
    elif buy_count > sell_count:
        return 'BUY'
    else:
        return 'SELL'

def main():
    """Fix SNAP recommendation and test the improved logic."""
    try:
        print("🔧 Fixing SNAP recommendation extraction...")
        
        from tradingagents.storage.neon_config import NeonConfig
        from tradingagents.storage.report_retrieval import ReportRetrievalService
        
        config = NeonConfig()
        service = ReportRetrievalService(config)
        
        # Test with SNAP session
        session_id = 'SNAP_2025-09-13_1757880827'
        result = service.get_final_analysis(session_id)
        
        if result:
            analysis = result.get('final_analysis', '')
            current_recommendation = result.get('recommendation', '')
            
            print(f"Current recommendation: {current_recommendation}")
            print("Testing improved extraction logic...")
            
            correct_recommendation = improved_extract_recommendation(analysis)
            print(f"Improved extraction result: {correct_recommendation}")
            
            if current_recommendation != correct_recommendation:
                print(f"🔄 Need to update: {current_recommendation} → {correct_recommendation}")
                
                # Update the database
                conn = None
                try:
                    conn = config.get_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE agent_reports 
                            SET recommendation = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE session_id = %s
                        """, (correct_recommendation, session_id))
                        
                        conn.commit()
                        print(f"✅ Updated SNAP recommendation to {correct_recommendation}")
                        
                finally:
                    if conn:
                        config.return_connection(conn)
            else:
                print("✅ Recommendation is already correct")
        
        print("🎉 SNAP recommendation fix completed!")
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())