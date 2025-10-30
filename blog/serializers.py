import uuid

import boto3
from botocore.exceptions import ClientError
from rest_framework import serializers
from .models import Post, Comment
from taggit.serializers import TaggitSerializer, TagListSerializerField

class PostSerializer(TaggitSerializer, serializers.ModelSerializer):
    author_nickname = serializers.SerializerMethodField()
    tags = TagListSerializerField()

    class Meta:
        model = Post
        fields = ['id', 'title', 'content', 'author_nickname', 'created_at', 'updated_at', 'tags']
        read_only_fields = ['author', 'created_at', 'updated_at']

    def get_author_nickname(self, obj):
        if obj.author.nickname:
            return obj.author.nickname
        else:
            return obj.author.username


class CommentSerializer(serializers.ModelSerializer):
    author_nickname = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = '__all__'
        read_only_fields = ['post', 'author_nickname', 'created_at', 'updated_at']

    def get_author_nickname(self, obj):
        if obj.author:
            return obj.author.nickname
        else:
            return obj.author_name