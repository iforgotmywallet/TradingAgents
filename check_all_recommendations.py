#!/usr/bin/env python3
"""
Check all sessions for recommendation consistency using the improved extraction logic.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

def improved_extract_recommendation(final_analysis: str) -> str:
    """Improved recommendation extraction logic."""
    if not final_analysis:
        return 'HOLD'
    
    analysis_upper = final_analysis.upper()
    
    # Look for explicit recommendation patterns first (more precise)
    recommendation_patterns = [
        r'RECOMMENDATION\s+IS\s+TO\s+(\w+)',
        r'RECOMMEND\s+(\w+)',
        r'MY\s+RECOMMENDATION\s+IS\s+(\w+)',
        r'\*\*(\w+)\*\*',
        r'IN\s+SUMMARY[:\s]*\*\*(\w+)\*\*',
        r'FINAL\s+RECOMMENDATION[:\s]*(\w+)',
    ]
    
    # First, try to find explicit recommendation patterns
    for pattern in recommendation_patterns:
        matches = re.findall(pattern, analysis_upper)
        for match in matches:
            if match in ['BUY', 'SELL', 'HOLD']:
                return match
    
    # If no explicit pattern found, look for contextual recommendations
    buy_contexts = len(re.findall(r'(?:RECOMMEND|SUGGESTION|DECISION).*?BUY', analysis_upper))
    sell_contexts = len(re.findall(r'(?:RECOMMEND|SUGGESTION|DECISION).*?SELL', analysis_upper))
    hold_contexts = len(re.findall(r'(?:RECOMMEND|SUGGESTION|DECISION).*?HOLD', analysis_upper))
    
    # Return the most contextually relevant recommendation
    if hold_contexts > max(buy_contexts, sell_contexts):
        return 'HOLD'
    elif buy_contexts > sell_contexts:
        return 'BUY'
    elif sell_contexts > buy_contexts:
        return 'SELL'
    
    # Fallback to careful word counting (standalone words only)
    buy_count = len(re.findall(r'\bBUY\b', analysis_upper))
    sell_count = len(re.findall(r'\bSELL\b', analysis_upper))
    hold_count = len(re.findall(r'\bHOLD\b', analysis_upper))
    
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
    """Check all sessions for recommendation consistency."""
    try:
        print("🔍 Checking all sessions for recommendation consistency...")
        
        from tradingagents.storage.neon_config import NeonConfig
        
        config = NeonConfig()
        
        conn = None
        try:
            conn = config.get_connection()
            with conn.cursor() as cursor:
                # Get all sessions with final_analysis
                cursor.execute("""
                    SELECT session_id, final_analysis, recommendation 
                    FROM agent_reports 
                    WHERE final_analysis IS NOT NULL
                    ORDER BY session_id
                """)
                
                sessions = cursor.fetchall()
                print(f"📊 Checking {len(sessions)} sessions...")
                
                inconsistent_sessions = []
                consistent_sessions = []
                
                for session in sessions:
                    session_id = session['session_id']
                    final_analysis = session['final_analysis']
                    current_recommendation = session['recommendation']
                    
                    if final_analysis:
                        # Extract recommendation using improved logic
                        correct_recommendation = improved_extract_recommendation(final_analysis)
                        
                        if current_recommendation != correct_recommendation:
                            inconsistent_sessions.append({
                                'session_id': session_id,
                                'current': current_recommendation,
                                'correct': correct_recommendation
                            })
                            print(f"❌ {session_id}: {current_recommendation} → {correct_recommendation}")
                        else:
                            consistent_sessions.append(session_id)
                            print(f"✅ {session_id}: {current_recommendation} (consistent)")
                
                print(f"\\n📊 Summary:")
                print(f"   ✅ Consistent sessions: {len(consistent_sessions)}")
                print(f"   ❌ Inconsistent sessions: {len(inconsistent_sessions)}")
                
                if inconsistent_sessions:
                    print(f"\\n🔧 Would you like to fix the inconsistent sessions? (y/n)")
                    # For now, just report them
                    print("\\nInconsistent sessions found:")
                    for session in inconsistent_sessions:
                        print(f"   {session['session_id']}: {session['current']} → {session['correct']}")
                
        finally:
            if conn:
                config.return_connection(conn)
        
        print("🎉 Recommendation consistency check completed!")
        
    except Exception as e:
        print(f"❌ Check failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())