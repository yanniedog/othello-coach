"""Self-play CLI for gauntlet matches"""

import argparse
import sys
from typing import List
from ..gauntlet.gauntlet import GauntletRunner
from ..engine.strength import get_available_profiles


def main():
    """Main entry point for othello-selfplay"""
    parser = argparse.ArgumentParser(
        description="Run self-play gauntlet matches for calibration"
    )
    
    parser.add_argument(
        '--games', 
        type=int, 
        default=100,
        help='Number of games per pairing (default: 100)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of worker threads (default: 4)'
    )
    
    parser.add_argument(
        '--profiles',
        nargs='+',
        default=['elo_400', 'elo_800', 'elo_1400', 'elo_2000', 'elo_2300'],
        help='Profiles to include in gauntlet'
    )
    
    parser.add_argument(
        '--custom-depth',
        type=int,
        help='Add custom depth profile (e.g., --custom-depth 8 adds depth_8)'
    )
    
    parser.add_argument(
        '--root-noise',
        action='store_true',
        default=True,
        help='Apply Dirichlet noise to root for first 6 moves'
    )
    
    parser.add_argument(
        '--no-root-noise',
        action='store_true',
        help='Disable root noise'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducibility'
    )
    
    parser.add_argument(
        '--db-path',
        default='~/.othello_coach/coach.sqlite',
        help='Database path'
    )
    
    parser.add_argument(
        '--output',
        help='Output file for match results (JSON)'
    )
    
    args = parser.parse_args()
    
    try:
        # Validate profiles
        available_profiles = get_available_profiles()
        for profile in args.profiles:
            if profile not in available_profiles and not profile.startswith('depth_'):
                print(f"Warning: Unknown profile '{profile}'", file=sys.stderr)
        
        # Add custom depth profile if specified
        if args.custom_depth:
            depth_profile = f'depth_{args.custom_depth}'
            if depth_profile not in args.profiles:
                args.profiles.append(depth_profile)
        
        # Set random seed if specified
        if args.seed:
            import random
            random.seed(args.seed)
            print(f"Using random seed: {args.seed}")
        
        # Determine root noise setting
        root_noise = args.root_noise and not args.no_root_noise
        
        print(f"Running gauntlet with {len(args.profiles)} profiles:")
        for profile in args.profiles:
            print(f"  - {profile}")
        print(f"Games per pairing: {args.games}")
        print(f"Workers: {args.workers}")
        print(f"Root noise: {root_noise}")
        print()
        
        # Run gauntlet
        runner = GauntletRunner(args.db_path)
        matches = runner.run_round_robin(
            profiles=args.profiles,
            games_per_pair=args.games,
            workers=args.workers,
            root_noise=root_noise
        )
        
        print(f"\nCompleted {len(matches)} matches")
        
        # Show results summary
        print("\nResults summary:")
        results = {}
        for match in matches:
            if match.result is not None:
                white = match.white_profile
                black = match.black_profile
                
                if white not in results:
                    results[white] = {'wins': 0, 'losses': 0, 'draws': 0, 'games': 0}
                if black not in results:
                    results[black] = {'wins': 0, 'losses': 0, 'draws': 0, 'games': 0}
                
                if match.result == 1.0:  # White wins
                    results[white]['wins'] += 1
                    results[black]['losses'] += 1
                elif match.result == 0.0:  # Black wins
                    results[white]['losses'] += 1
                    results[black]['wins'] += 1
                else:  # Draw
                    results[white]['draws'] += 1
                    results[black]['draws'] += 1
                
                results[white]['games'] += 1
                results[black]['games'] += 1
        
        for profile in sorted(results.keys()):
            stats = results[profile]
            if stats['games'] > 0:
                win_rate = stats['wins'] / stats['games']
                print(f"{profile:12s}: {stats['wins']:3d}W {stats['losses']:3d}L {stats['draws']:3d}D ({win_rate:.1%})")
        
        # Show updated ladder
        print("\nUpdated ladder:")
        standings = runner.get_ladder_standings()
        for i, (profile, rating) in enumerate(standings, 1):
            print(f"{i:2d}. {profile:12s}: {rating.rating:4.0f} ± {rating.rd:3.0f}")
        
        # Save results if requested
        if args.output:
            import json
            from datetime import datetime
            
            output_data = {
                'timestamp': datetime.now().isoformat(),
                'config': {
                    'profiles': args.profiles,
                    'games_per_pair': args.games,
                    'workers': args.workers,
                    'root_noise': root_noise,
                    'seed': args.seed
                },
                'matches': [
                    {
                        'white_profile': m.white_profile,
                        'black_profile': m.black_profile,
                        'result': m.result,
                        'game_length': m.game_length,
                        'moves': m.moves
                    }
                    for m in matches if m.result is not None
                ],
                'ladder': [
                    {
                        'profile': profile,
                        'rating': rating.rating,
                        'rd': rating.rd,
                        'games_played': rating.games_played
                    }
                    for profile, rating in standings
                ]
            }
            
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\nResults saved to {args.output}")
        
    except KeyboardInterrupt:
        print("\nGauntlet interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error running gauntlet: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
