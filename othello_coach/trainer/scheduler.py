"""Leitner spaced repetition scheduler"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


@dataclass
class TrainerItem:
    """Item in the training queue"""
    hash: int
    box: int
    due: Optional[date]
    streak: int
    suspended: bool
    item_type: str  # 'tactics', 'parity', 'endgame'
    content: Dict  # position data, hints, etc.


class LeitnerScheduler:
    """Implements Leitner spaced repetition system"""
    
    def __init__(self, db_path: str, leitner_days: List[int] = None):
        self.leitner_days = leitner_days or [1, 3, 7, 14, 30]
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.Session = sessionmaker(bind=self.engine)
    
    def get_daily_queue(self, max_items: int = 30, 
                       new_to_review_ratio: str = "3:7") -> List[TrainerItem]:
        """Get today's training queue"""
        new_ratio, review_ratio = map(int, new_to_review_ratio.split(':'))
        total_ratio = new_ratio + review_ratio
        
        max_new = (max_items * new_ratio) // total_ratio
        max_review = max_items - max_new
        
        today = date.today()
        items = []
        
        with self.Session() as session:
            # Get review items (due today or overdue)
            review_query = text("""
                SELECT hash, box, due, streak, suspended
                FROM trainer 
                WHERE due <= :today AND suspended = 0
                ORDER BY due ASC, box ASC
                LIMIT :max_review
            """)
            review_results = session.execute(
                review_query, 
                {'today': today, 'max_review': max_review}
            ).fetchall()
            
            for row in review_results:
                item = self._load_trainer_item(row.hash, row.box, row.due, 
                                             row.streak, bool(row.suspended))
                if item:
                    items.append(item)
            
            # Fill remaining slots with new items
            remaining_slots = max_items - len(items)
            if remaining_slots > 0:
                new_query = text("""
                    SELECT p.hash, p.black, p.white, p.stm, p.ply
                    FROM positions p
                    LEFT JOIN trainer t ON p.hash = t.hash
                    WHERE t.hash IS NULL
                    ORDER BY RANDOM()
                    LIMIT :limit
                """)
                new_results = session.execute(
                    new_query, 
                    {'limit': remaining_slots}
                ).fetchall()
                
                for row in new_results:
                    # Create new trainer item
                    item = self._create_new_item(row.hash, row.black, row.white, 
                                               row.stm, row.ply)
                    if item:
                        items.append(item)
                        # Add to database
                        self._add_new_item(session, item)
            
            session.commit()
        
        return items
    
    def _load_trainer_item(self, hash_val: int, box: int, due: date, 
                          streak: int, suspended: bool) -> Optional[TrainerItem]:
        """Load trainer item with content"""
        # Determine item type and load content
        # This would be expanded based on how content is stored
        return TrainerItem(
            hash=hash_val,
            box=box,
            due=due,
            streak=streak,
            suspended=suspended,
            item_type='tactics',  # Default for now
            content={'hash': hash_val}
        )
    
    def _create_new_item(self, hash_val: int, black: int, white: int, 
                        stm: int, ply: int) -> Optional[TrainerItem]:
        """Create new trainer item from position"""
        # Determine what type of training item this should be
        item_type = self._classify_position(black, white, stm, ply)
        
        if item_type:
            return TrainerItem(
                hash=hash_val,
                box=1,
                due=date.today(),
                streak=0,
                suspended=False,
                item_type=item_type,
                content={
                    'hash': hash_val,
                    'black': black,
                    'white': white,
                    'stm': stm,
                    'ply': ply
                }
            )
        return None
    
    def _classify_position(self, black: int, white: int, stm: int, ply: int) -> Optional[str]:
        """Classify position for training type"""
        empty_count = 64 - bin(black | white).count('1')
        
        if empty_count <= 16:
            return 'endgame'
        elif empty_count >= 40:
            return 'parity'
        else:
            return 'tactics'
    
    def _add_new_item(self, session, item: TrainerItem):
        """Add new item to database"""
        insert_query = text("""
            INSERT INTO trainer (hash, box, due, streak, suspended)
            VALUES (:hash, :box, :due, :streak, :suspended)
        """)
        session.execute(insert_query, {
            'hash': item.hash,
            'box': item.box,
            'due': item.due,
            'streak': item.streak,
            'suspended': int(item.suspended)
        })
    
    def record_result(self, item: TrainerItem, success: bool):
        """Record training result and update schedule"""
        with self.Session() as session:
            if success:
                # Move to next box
                new_box = min(item.box + 1, len(self.leitner_days))
                new_streak = item.streak + 1
                new_due = date.today() + timedelta(days=self.leitner_days[new_box - 1])
                suspended = False
            else:
                # Reset to box 1, increment failure count
                new_box = 1
                new_streak = 0
                new_due = date.today() + timedelta(days=self.leitner_days[0])
                
                # Check for auto-suspend (3 consecutive failures)
                suspended = item.streak >= 3
                if suspended:
                    new_due = date.today() + timedelta(days=2)  # 48h suspension
            
            update_query = text("""
                UPDATE trainer 
                SET box = :box, due = :due, streak = :streak, suspended = :suspended
                WHERE hash = :hash
            """)
            session.execute(update_query, {
                'box': new_box,
                'due': new_due,
                'streak': new_streak,
                'suspended': int(suspended),
                'hash': item.hash
            })
            session.commit()
    
    def get_progress_stats(self) -> Dict:
        """Get training progress statistics"""
        with self.Session() as session:
            stats_query = text("""
                SELECT 
                    box,
                    COUNT(*) as count,
                    AVG(streak) as avg_streak
                FROM trainer
                WHERE suspended = 0
                GROUP BY box
                ORDER BY box
            """)
            results = session.execute(stats_query).fetchall()
            
            stats = {
                'boxes': {},
                'total_active': 0,
                'suspended_count': 0
            }
            
            for row in results:
                stats['boxes'][row.box] = {
                    'count': row.count,
                    'avg_streak': round(row.avg_streak, 1)
                }
                stats['total_active'] += row.count
            
            # Get suspended count
            suspended_query = text("SELECT COUNT(*) FROM trainer WHERE suspended = 1")
            stats['suspended_count'] = session.execute(suspended_query).scalar()
        
        return stats
    
    def resume_suspended_items(self):
        """Resume items that have been suspended for 48+ hours"""
        cutoff = date.today() - timedelta(days=2)
        
        with self.Session() as session:
            resume_query = text("""
                UPDATE trainer 
                SET suspended = 0, due = :today
                WHERE suspended = 1 AND due <= :cutoff
            """)
            session.execute(resume_query, {
                'today': date.today(),
                'cutoff': cutoff
            })
            session.commit()
