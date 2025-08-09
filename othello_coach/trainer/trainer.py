"""Main trainer orchestrator"""

from typing import List, Dict, Optional
from datetime import date
from .scheduler import LeitnerScheduler, TrainerItem
from .tactics import TacticsGenerator, TacticsPuzzle
from .drills import ParityDrills, EndgameDrills, ParityDrill, EndgameDrill


class Trainer:
    """Main training system coordinator"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.scheduler = LeitnerScheduler(
            db_path=config['db']['path'],
            leitner_days=config['trainer']['leitner_days']
        )
        
        self.tactics_generator = TacticsGenerator()
        self.parity_drills = ParityDrills()
        self.endgame_drills = EndgameDrills()
        
        # Load configuration
        self.daily_cap = config['trainer']['daily_review_cap']
        self.new_to_review_ratio = config['trainer']['new_to_review_ratio']
        self.auto_suspend = config['trainer']['auto_suspend_on_3_fails']
    
    def get_daily_session(self) -> List[TrainerItem]:
        """Get today's training session"""
        # Resume any suspended items first
        self.scheduler.resume_suspended_items()
        
        # Get the daily queue
        items = self.scheduler.get_daily_queue(
            max_items=self.daily_cap,
            new_to_review_ratio=self.new_to_review_ratio
        )
        
        # Enrich items with specific drill content
        enriched_items = []
        for item in items:
            enriched_item = self._enrich_trainer_item(item)
            if enriched_item:
                enriched_items.append(enriched_item)
        
        return enriched_items
    
    def _enrich_trainer_item(self, item: TrainerItem) -> Optional[TrainerItem]:
        """Add specific drill content to trainer item"""
        try:
            # Reconstruct board from content
            board = self._item_to_board(item)
            
            if item.item_type == 'tactics':
                puzzle = self.tactics_generator.generate_puzzle(board)
                if puzzle:
                    item.content.update({
                        'puzzle': puzzle,
                        'hint': puzzle.hint_text,
                        'difficulty': puzzle.difficulty
                    })
            
            elif item.item_type == 'parity':
                drill = self.parity_drills.generate_drill(board)
                if drill:
                    item.content.update({
                        'drill': drill,
                        'explanation': drill.explanation
                    })
            
            elif item.item_type == 'endgame':
                drill = self.endgame_drills.generate_drill(board)
                if drill:
                    item.content.update({
                        'drill': drill,
                        'empties': drill.empties,
                        'time_limit': drill.time_limit
                    })
            
            return item
            
        except Exception:
            return None
    
    def _item_to_board(self, item: TrainerItem):
        """Convert trainer item to board"""
        from ..engine.board import Board
        return Board(
            B=item.content['black'],
            W=item.content['white'],
            stm=item.content['stm'],
            ply=item.content['ply'],
            hash=item.content['hash']
        )
    
    def submit_answer(self, item: TrainerItem, user_answer: Dict) -> Dict:
        """Process user's answer and update scheduler"""
        result = {'success': False, 'feedback': '', 'explanation': ''}
        
        try:
            if item.item_type == 'tactics':
                puzzle = item.content.get('puzzle')
                if puzzle:
                    user_move = user_answer.get('move')
                    validation = self.tactics_generator.validate_solution(puzzle, user_move)
                    result['success'] = validation['correct']
                    result['feedback'] = validation['explanation']
            
            elif item.item_type == 'parity':
                drill = item.content.get('drill')
                if drill:
                    user_move = user_answer.get('move')
                    validation = self.parity_drills.validate_solution(drill, user_move)
                    result['success'] = validation['correct']
                    result['feedback'] = validation['feedback']
            
            elif item.item_type == 'endgame':
                drill = item.content.get('drill')
                if drill:
                    user_move = user_answer.get('move')
                    time_taken = user_answer.get('time_taken', 999)
                    validation = self.endgame_drills.validate_solution(drill, user_move, time_taken)
                    result['success'] = validation['correct']
                    result['feedback'] = validation['feedback']
                    result['time_bonus'] = validation.get('time_bonus', 0)
            
            # Update scheduler with result
            self.scheduler.record_result(item, result['success'])
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'feedback': f'Error processing answer: {str(e)}',
                'explanation': ''
            }
    
    def get_progress_report(self) -> Dict:
        """Get comprehensive progress report"""
        stats = self.scheduler.get_progress_stats()
        
        # Add additional metrics
        report = {
            'scheduler_stats': stats,
            'daily_completion': self._get_daily_completion(),
            'strengths_weaknesses': self._analyze_performance(),
            'next_session_preview': self._preview_next_session()
        }
        
        return report
    
    def _get_daily_completion(self) -> Dict:
        """Get today's completion status"""
        # Would track completed items vs. total for today
        return {
            'completed': 0,  # Would be tracked in session
            'total': self.daily_cap,
            'percentage': 0.0
        }
    
    def _analyze_performance(self) -> Dict:
        """Analyze user's performance patterns"""
        # Would analyze success rates by type, difficulty, etc.
        return {
            'tactics_accuracy': 0.0,
            'parity_accuracy': 0.0,
            'endgame_accuracy': 0.0,
            'improvement_areas': []
        }
    
    def _preview_next_session(self) -> Dict:
        """Preview what's coming in next session"""
        tomorrow_items = self.scheduler.get_daily_queue(max_items=5)
        
        return {
            'estimated_items': len(tomorrow_items),
            'types_preview': {
                'tactics': sum(1 for item in tomorrow_items if item.item_type == 'tactics'),
                'parity': sum(1 for item in tomorrow_items if item.item_type == 'parity'),
                'endgame': sum(1 for item in tomorrow_items if item.item_type == 'endgame')
            }
        }
    
    def add_custom_position(self, board, item_type: str = 'tactics'):
        """Add a custom position to the training queue"""
        from datetime import date
        
        item = TrainerItem(
            hash=board.hash,
            box=1,
            due=date.today(),
            streak=0,
            suspended=False,
            item_type=item_type,
            content={
                'hash': board.hash,
                'black': board.B,
                'white': board.W,
                'stm': board.stm,
                'ply': board.ply
            }
        )
        
        # Add to database
        with self.scheduler.Session() as session:
            self.scheduler._add_new_item(session, item)
            session.commit()
