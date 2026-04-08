"""Phase F: KPI Tracking for user testing and productivity measurement.

Tracks:
- Decision time per image
- Error rate vs. auto-recommendations
- Total decisions by type (Keep/Delete/Unsure)
- Session statistics

For user testing validation (Phase F).
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DecisionRecord:
    """Single decision record for a file."""
    file_path: str
    decision: str  # "KEEP", "DELETE", "UNSURE"
    timestamp: float  # Unix timestamp
    decision_time_ms: float  # Time spent on this decision
    auto_recommendation: Optional[str] = None  # What system recommended (if any)
    is_correct_vs_auto: Optional[bool] = None  # True if matches auto-recommendation
    user_email: Optional[str] = None  # Optional user identifier
    notes: Optional[str] = None


@dataclass
class KPISession:
    """Session-level KPI statistics."""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    decisions: List[DecisionRecord] = field(default_factory=list)
    user_email: Optional[str] = None
    test_mode: bool = True  # Testing/validation mode
    
    def add_decision(self, record: DecisionRecord) -> None:
        """Record a single decision."""
        self.decisions.append(record)
    
    def get_statistics(self) -> Dict:
        """Calculate session statistics."""
        if not self.decisions:
            return {
                "total_decisions": 0,
                "session_duration_seconds": 0,
                "average_decision_time_ms": 0,
                "decisions_by_type": {},
                "accuracy_vs_auto": None,
            }
        
        duration = (self.end_time or time.time()) - self.start_time
        
        # Count by type
        decisions_by_type = {
            "KEEP": sum(1 for d in self.decisions if d.decision == "KEEP"),
            "DELETE": sum(1 for d in self.decisions if d.decision == "DELETE"),
            "UNSURE": sum(1 for d in self.decisions if d.decision == "UNSURE"),
        }
        
        # Average decision time
        avg_decision_time = sum(d.decision_time_ms for d in self.decisions) / len(self.decisions)
        
        # Accuracy vs auto-recommendations
        auto_decisions = [d for d in self.decisions if d.auto_recommendation is not None]
        if auto_decisions:
            correct = sum(1 for d in auto_decisions if d.is_correct_vs_auto)
            accuracy = correct / len(auto_decisions)
        else:
            accuracy = None
        
        return {
            "total_decisions": len(self.decisions),
            "session_duration_seconds": duration,
            "average_decision_time_ms": avg_decision_time,
            "decisions_by_type": decisions_by_type,
            "accuracy_vs_auto": accuracy,
        }


class KPITracker:
    """Central KPI tracking for Phase F user testing."""
    
    def __init__(self, test_mode: bool = True):
        """Initialize tracker (test_mode=True for user testing)."""
        self.test_mode = test_mode
        self.current_session: Optional[KPISession] = None
        self._decision_start_time: Optional[float] = None
        self._sessions_history: List[KPISession] = []
    
    def start_session(self, user_email: Optional[str] = None) -> KPISession:
        """Start a new KPI tracking session."""
        session_id = f"session_{int(time.time() * 1000)}"
        self.current_session = KPISession(
            session_id=session_id,
            start_time=time.time(),
            user_email=user_email,
            test_mode=self.test_mode,
        )
        logger.info(f"[KPI] Started session {session_id} (test_mode={self.test_mode})")
        return self.current_session
    
    def mark_decision_started(self) -> None:
        """Mark the start of a decision (timestamp for decision_time_ms)."""
        self._decision_start_time = time.time()
    
    def record_decision(
        self,
        file_path: str,
        decision: str,
        auto_recommendation: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Record a decision with timing information."""
        if not self.current_session:
            logger.warning("[KPI] No active session; starting new session")
            self.start_session()
        
        if not self._decision_start_time:
            # Use default if not marked
            decision_time_ms = 0
        else:
            decision_time_ms = (time.time() - self._decision_start_time) * 1000
        
        # Determine if correct vs auto
        is_correct = None
        if auto_recommendation and decision == auto_recommendation:
            is_correct = True
        elif auto_recommendation:
            is_correct = False
        
        record = DecisionRecord(
            file_path=str(file_path),
            decision=decision,
            timestamp=time.time(),
            decision_time_ms=decision_time_ms,
            auto_recommendation=auto_recommendation,
            is_correct_vs_auto=is_correct,
            notes=notes,
        )
        
        self.current_session.add_decision(record)
        self._decision_start_time = None  # Reset timer
        
        logger.debug(f"[KPI] Decision recorded: {decision} for {Path(file_path).name} ({decision_time_ms:.0f}ms)")
    
    def end_session(self) -> Optional[Dict]:
        """End current session and return statistics."""
        if not self.current_session:
            return None
        
        self.current_session.end_time = time.time()
        stats = self.current_session.get_statistics()
        
        self._sessions_history.append(self.current_session)
        logger.info(f"[KPI] Session ended: {stats}")
        
        return stats
    
    def export_to_json(self, output_path: Path) -> Path:
        """Export all session data to JSON."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        export_data = {
            "export_time": datetime.now().isoformat(),
            "test_mode": self.test_mode,
            "sessions": [],
        }
        
        for session in self._sessions_history:
            session_data = {
                "session_id": session.session_id,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "user_email": session.user_email,
                "test_mode": session.test_mode,
                "statistics": session.get_statistics(),
                "decisions": [asdict(d) for d in session.decisions],
            }
            export_data["sessions"].append(session_data)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[KPI] Exported {len(self._sessions_history)} session(s) to {output_path}")
        return output_path
    
    def get_current_statistics(self) -> Optional[Dict]:
        """Get statistics for current session (if active)."""
        if not self.current_session:
            return None
        return self.current_session.get_statistics()
    
    def get_all_sessions_statistics(self) -> Dict:
        """Get aggregated statistics for all sessions."""
        if not self._sessions_history:
            return {"total_sessions": 0, "total_decisions": 0}
        
        total_decisions = sum(len(s.decisions) for s in self._sessions_history)
        total_duration = sum((s.end_time or time.time()) - s.start_time for s in self._sessions_history)
        
        # Aggregate by type
        all_by_type = {
            "KEEP": 0,
            "DELETE": 0,
            "UNSURE": 0,
        }
        for session in self._sessions_history:
            for decision in session.decisions:
                all_by_type[decision.decision] += 1
        
        # Aggregate accuracy
        auto_decisions = sum(
            1 for s in self._sessions_history for d in s.decisions if d.auto_recommendation is not None
        )
        correct_decisions = sum(
            1 for s in self._sessions_history for d in s.decisions
            if d.auto_recommendation and d.is_correct_vs_auto
        )
        accuracy = correct_decisions / auto_decisions if auto_decisions > 0 else None
        
        return {
            "total_sessions": len(self._sessions_history),
            "total_decisions": total_decisions,
            "total_duration_seconds": total_duration,
            "average_session_duration_seconds": total_duration / len(self._sessions_history),
            "decisions_by_type": all_by_type,
            "overall_accuracy_vs_auto": accuracy,
        }


# Global tracker instance
_kpi_tracker: Optional[KPITracker] = None


def get_kpi_tracker(test_mode: bool = True) -> KPITracker:
    """Get or create global KPI tracker."""
    global _kpi_tracker
    if _kpi_tracker is None:
        _kpi_tracker = KPITracker(test_mode=test_mode)
    return _kpi_tracker


def reset_kpi_tracker() -> None:
    """Reset global tracker (for testing)."""
    global _kpi_tracker
    _kpi_tracker = None
