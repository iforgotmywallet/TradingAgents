#!/usr/bin/env python3
"""
Script to fix recommendation consistency issues.

This script:
1. Removes the final_decision column (if it exists)
2. Updates recommendation column to match final_analysis content
3. Ensures consistency between final_analysis and recommendation
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

def main():
    """Fix recommendation consistency issues."""
    try:
        print("🔄 Fixing recommendation consistency...")
        
        # Check if database URL is available
        if not os.getenv('NEON_DATABASE_URL'):
            print("⚠️  NEON_DATABASE_URL not set. Please set it to run database operations.")
            print("This script will:")
            print("1. Remove final_decision column from database")
            print("2. Update recommendation to match final_analysis")
            print("3. Ensure consistency between final_analysis and recommendation")
            return 0
        
        from tradingagents.storage.neon_config import NeonConfig
        from tradingagents.storage.migrations import MigrationRunner
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        
        # Initialize config
        config = NeonConfig()
        
        # Step 1: Run migration to remove final_decision column
        print("📋 Step 1: Running database migration...")
        runner = MigrationRunner(config)
        applied_count = runner.run_migrations()
        
        if applied_count > 0:
            print(f"✅ Applied {applied_count} migration(s)")
        else:
            print("✅ No new migrations to apply")
        
        # Step 2: Fix recommendation consistency
        print("📋 Step 2: Fixing recommendation consistency...")
        
        conn = None
        try:
            conn = config.get_connection()
            with conn.cursor() as cursor:
                # Get all sessions with final_analysis but inconsistent recommendations
                cursor.execute("""
                    SELECT session_id, final_analysis, recommendation 
                    FROM agent_reports 
                    WHERE final_analysis IS NOT NULL
                """)
                
                sessions = cursor.fetchall()
                updated_count = 0
                
                for session in sessions:
                    session_id = session['session_id']
                    final_analysis = session['final_analysis']
                    current_recommendation = session['recommendation']
                    
                    if final_analysis:
                        # Extract recommendation from final_analysis using the same logic as TradingAgentsGraph
                        graph = TradingAgentsGraph([], {}, debug=False)
                        correct_recommendation = graph._extract_recommendation(final_analysis)
                        
                        if current_recommendation != correct_recommendation:
                            print(f"🔄 Updating {session_id}: {current_recommendation} → {correct_recommendation}")
                            
                            # Update the recommendation
                            cursor.execute("""
                                UPDATE agent_reports 
                                SET recommendation = %s, updated_at = CURRENT_TIMESTAMP
                                WHERE session_id = %s
                            """, (correct_recommendation, session_id))
                            
                            updated_count += 1
                        else:
                            print(f"✅ {session_id}: Already consistent ({current_recommendation})")
                
                conn.commit()
                print(f"✅ Updated {updated_count} sessions for consistency")
                
        finally:
            if conn:
                config.return_connection(conn)
        
        print("🎉 Recommendation consistency fix completed!")
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())