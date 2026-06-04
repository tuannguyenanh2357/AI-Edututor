from rest_framework import serializers
from .models import Badge, UserBadge, StoreItem, Inventory
from django.contrib.auth import get_user_model

User = get_user_model()

class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = '__all__'

class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)
    class Meta:
        model = UserBadge
        fields = ['badge', 'earned_at']

class StoreItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreItem
        fields = '__all__'

class UserInventorySerializer(serializers.ModelSerializer):
    item = StoreItemSerializer(read_only=True)
    class Meta:
        model = Inventory
        fields = ['id', 'item', 'quantity', 'acquired_at', 'is_used']

class LeaderboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'total_xp', 'current_streak', 'gems', 'rank', 'avatar_url']
