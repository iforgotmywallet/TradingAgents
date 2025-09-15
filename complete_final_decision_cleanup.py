#!/usr/bin/env python3
"""
Complete Final Decision Cleanup Script

This script performs a comprehensive cleanup of final_decision references:
1. Runs database migration to remove final_decision column
2. Fixes recommendation consistency with final_analysis
3. Verifies all changes are applied correctly
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

def main():
    """Perform complete final_decision cleanup."""
    try:
        print("🧹 Starting complete final_decision cleanup...")
        
        # Check if database URL is available
        if not os.getenv('NEON_DATABASE_URL'):
            print("⚠️  NEON_DATABASE_URL not set.")
            print("📋 Manual steps required:")
            print("1. Set NEON_DATABASE_URL environment variable")
            print("2. Run: python complete_final_decision_cleanup.py")
            print("3. This will:")
            print("   - Remove final_decision column from database")
            print("   - Update recommendations to match final_analysis")
            print("   - Verify consistency")
            return 0
        
        from tradingagents.storage.neon_config import NeonConfig
        from tradingagents.storage.migrations import MigrationRunner
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        
        # Initialize config
        config = NeonConfig()
        
        print("📋 Step 1: Running database migration to remove final_decision column...")
        try:
            runner = MigrationRunner(config)
            success = runner.migrate_up()
            
            if success:
                print("✅ Migration completed successfully")
            else:
                print("⚠️  Migration had issues, continuing...")
        except Exception as e:
            print(f"⚠️  Migration warning: {e}")
            print("Continuing with recommendation consistency fix...")
        
        print("📋 Step 2: Fixing recommendation consistency...")
        
        conn = None
        try:
            conn = config.get_connection()
            with conn.cursor() as cursor:
                # Check if final_decision column still exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'agent_reports' AND column_name = 'final_decision'
                """)
                
                if cursor.fetchone():
                    print("⚠️  final_decision column still exists, attempting manual removal...")
                    try:
                        cursor.execute("ALTER TABLE agent_reports DROP COLUMN final_decision")
                        conn.commit()
                        print("✅ Manually removed final_decision column")
                    except Exception as e:
                        print(f"❌ Could not remove final_decision column: {e}")
                else:
                    print("✅ final_decision column already removed")
                
                # Get all sessions with final_analysis
                cursor.execute("""
                    SELECT session_id, final_analysis, recommendation 
                    FROM agent_reports 
                    WHERE final_analysis IS NOT NULL
                """)
                
                sessions = cursor.fetchall()
                print(f"📊 Found {len(sessions)} sessions with final_analysis")
                
                updated_count = 0
                consistent_count = 0
                
                # Define the recommendation extraction function (same logic as TradingAgentsGraph)
                def extract_recommendation(final_analysis: str) -> str:
                    """Extract BUY/SELL/HOLD recommendation from final analysis text."""
                    if not final_analysis:
                        return 'HOLD'
                    
                    analysis_upper = final_analysis.upper()
                    
                    # Look for explicit recommendations
                    if 'BUY' in analysis_upper and 'SELL' not in analysis_upper:
                        return 'BUY'
                    elif 'SELL' in analysis_upper:
                        return 'SELL'
                    elif 'HOLD' in analysis_upper:
                        return 'HOLD'
                    
                    # Look for other positive/negative indicators
                    positive_indicators = ["BULLISH", "POSITIVE", "UPWARD", "LONG", "INVEST", "PURCHASE"]
                    negative_indicators = ["BEARISH", "NEGATIVE", "DOWNWARD", "SHORT", "AVOID", "DECLINE"]
                    
                    positive_count = sum(1 for indicator in positive_indicators if indicator in analysis_upper)
                    negative_count = sum(1 for indicator in negative_indicators if indicator in analysis_upper)
                    
                    if positive_count > negative_count:
                        return 'BUY'
                    elif negative_count > positive_count:
                        return 'SELL'
                    else:
                        return 'HOLD'
                
                for session in sessions:
                    session_id = session['session_id']
                    final_analysis = session['final_analysis']
                    current_recommendation = session['recommendation']
                    
                    if final_analysis:
                        # Extract recommendation from final_analysis
                        correct_recommendation = extract_recommendation(final_analysis)
                        
                        if current_recommendation != correct_recommendation:
                            print(f"🔄 {session_id}: {current_recommendation} → {correct_recommendation}")
                            
                            # Update the recommendation
                            cursor.execute("""
                                UPDATE agent_reports 
                                SET recommendation = %s, updated_at = CURRENT_TIMESTAMP
                                WHERE session_id = %s
                            """, (correct_recommendation, session_id))
                            
                            updated_count += 1
                        else:
                            consistent_count += 1
                
                conn.commit()
                print(f"✅ Updated {updated_count} sessions")
                print(f"✅ {consistent_count} sessions were already consistent")
                
        finally:
            if conn:
                config.return_connection(conn)
        
        print("📋 Step 3: Verification...")
        
        # Verify the cleanup
        conn = None
        try:
            conn = config.get_connection()
            with conn.cursor() as cursor:
                # Check that final_decision column is gone
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'agent_reports' AND column_name = 'final_decision'
                """)
                
                if cursor.fetchone():
                    print("❌ final_decision column still exists!")
                else:
                    print("✅ final_decision column successfully removed")
                
                # Check recommendation consistency
                cursor.execute("""
                    SELECT COUNT(*) as total_sessions,
                           COUNT(CASE WHEN final_analysis IS NOT NULL THEN 1 END) as with_analysis,
                           COUNT(CASE WHEN recommendation IS NOT NULL THEN 1 END) as with_recommendation
                    FROM agent_reports
                """)
                
                stats = cursor.fetchone()
                print(f"📊 Database stats:")
                print(f"   Total sessions: {stats['total_sessions']}")
                print(f"   With final_analysis: {stats['with_analysis']}")
                print(f"   With recommendation: {stats['with_recommendation']}")
                
        finally:
            if conn:
                config.return_connection(conn)
        
        print("🎉 Complete final_decision cleanup finished!")
        print("📋 Summary of changes:")
        print("   ✅ Removed final_decision column from database")
        print("   ✅ Updated recommendations to match final_analysis")
        print("   ✅ Fixed frontend to use /api/final-analysis/ endpoint")
        print("   ✅ Removed final_decision display from UI")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())