#!/usr/bin/env python3
"""Test gauntlet performance to confirm no delays are introduced"""

import time
import logging
from othello_coach.gauntlet.gauntlet import GauntletRunner

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_gauntlet_performance():
    """Test gauntlet performance with timing measurements"""
    print("🧪 Testing gauntlet performance...")
    
    # Create gauntlet runner
    runner = GauntletRunner(":memory:")
    
    # Progress callback to track timing
    match_times = []
    last_update = time.time()
    
    def progress_callback(message, percentage):
        nonlocal last_update
        current_time = time.time()
        elapsed = current_time - last_update
        
        if "Match " in message and "/" in message:
            match_times.append(elapsed)
            print(f"⏱️  Match completed in {elapsed:.3f}s: {message}")
        else:
            print(f"📊 {message}")
            
        last_update = current_time
    
    # Run a small gauntlet for testing
    start_time = time.time()
    
    try:
        matches = runner.run_round_robin(
            profiles=['elo_400', 'elo_800'],
            games_per_pair=10,  # Small number for testing
            workers=2,
            root_noise=False,
            progress_callback=progress_callback
        )
        
        total_time = time.time() - start_time
        
        print(f"\n✅ Gauntlet completed in {total_time:.3f}s")
        print(f"📈 Total matches: {len(matches)}")
        print(f"⚡ Average time per match: {total_time/len(matches):.3f}s")
        
        if match_times:
            avg_match_time = sum(match_times) / len(match_times)
            max_match_time = max(match_times)
            min_match_time = min(match_times)
            
            print(f"🎯 Match timing analysis:")
            print(f"   - Average: {avg_match_time:.3f}s")
            print(f"   - Fastest: {min_match_time:.3f}s")
            print(f"   - Slowest: {max_match_time:.3f}s")
            
            # Check for any suspicious delays
            if max_match_time > 5.0:
                print(f"⚠️  Warning: Some matches took longer than 5 seconds")
            elif max_match_time > 2.0:
                print(f"⚠️  Warning: Some matches took longer than 2 seconds")
            else:
                print(f"✅ All matches completed within reasonable time")
        
        # Show results
        print(f"\n🏆 Results summary:")
        for match in matches:
            result_str = "W" if match.result == 1.0 else "B" if match.result == 0.0 else "D"
            print(f"   {match.white_profile} vs {match.black_profile}: {result_str} ({match.game_length} moves)")
            
    except Exception as e:
        print(f"❌ Gauntlet failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gauntlet_performance()
