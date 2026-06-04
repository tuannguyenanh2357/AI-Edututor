# Re-export all views for clean imports in urls.py
from .challenge_views import ChallengeSendView, PendingBattlesView
from .battle_views import BattleDetailView, BattleAcceptView, BattleDeclineView, BattleSubmitView
from .result_views import BattleStatusView, BattleHistoryView

__all__ = [
    'ChallengeSendView',
    'PendingBattlesView',
    'BattleDetailView',
    'BattleAcceptView',
    'BattleDeclineView',
    'BattleSubmitView',
    'BattleStatusView',
    'BattleHistoryView',
]
