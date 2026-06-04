from django.urls import path
from .views import (
    ChallengeSendView,
    PendingBattlesView,
    BattleDetailView,
    BattleAcceptView,
    BattleDeclineView,
    BattleSubmitView,
    BattleStatusView,
    BattleHistoryView,
)

urlpatterns = [
    # Challenge management
    path('challenge/',          ChallengeSendView.as_view(),  name='battle-challenge'),
    path('pending/',            PendingBattlesView.as_view(), name='battle-pending'),
    path('history/',            BattleHistoryView.as_view(),  name='battle-history'),

    # Per-battle actions
    path('<int:battle_id>/',          BattleDetailView.as_view(), name='battle-detail'),
    path('<int:battle_id>/accept/',   BattleAcceptView.as_view(),  name='battle-accept'),
    path('<int:battle_id>/decline/',  BattleDeclineView.as_view(), name='battle-decline'),
    path('<int:battle_id>/submit/',   BattleSubmitView.as_view(),  name='battle-submit'),
    path('<int:battle_id>/status/',   BattleStatusView.as_view(), name='battle-status'),
]
