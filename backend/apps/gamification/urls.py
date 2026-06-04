from django.urls import path
from .views import (
    DailyQuestView, SubmitQuestView, LeaderboardView, 
    UserBadgesView, AllBadgesView, RecentBadgesView, StoreItemListView, 
    PurchaseItemView, UserInventoryListView
)

urlpatterns = [
    path('daily-quest/', DailyQuestView.as_view(), name='daily-quest'),
    path('submit-quest/', SubmitQuestView.as_view(), name='submit-quest'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('badges/', UserBadgesView.as_view(), name='user-badges'),
    path('all-badges/', AllBadgesView.as_view(), name='all-badges'),
    path('recent-badges/', RecentBadgesView.as_view(), name='recent-badges'),
    path('store/', StoreItemListView.as_view(), name='store-list'),
    path('inventory/', UserInventoryListView.as_view(), name='inventory-list'),
    path('purchase/', PurchaseItemView.as_view(), name='purchase-item'),
]
