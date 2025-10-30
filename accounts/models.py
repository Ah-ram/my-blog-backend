from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    github_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    nickname = models.CharField(max_length=20, unique=True, null=True, blank=True)

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'user'