from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=120, default='New chat')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    summary = models.TextField(blank=True, default='')

    class Meta:
        ordering = ('-updated_at',)

    def __str__(self):
        return self.title


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    )

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ('created_at',)

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"


class UserPreference(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_preferences')
    preferences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Lead(models.Model):
    name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField(blank=True)
    source = models.CharField(max_length=50, default='chat')
    created_at = models.DateTimeField(auto_now_add=True)


class RecommendationLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    session = models.ForeignKey(ChatSession, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey('api.Product', on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class BrowseHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    session = models.ForeignKey(ChatSession, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey('api.Product', on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-viewed_at',)
