from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import models
from taggit.managers import TaggableManager

class Post(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200, verbose_name='제목')
    content = models.TextField(verbose_name='내용')
    author = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, verbose_name='작성자')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    tags = TaggableManager(verbose_name='태그')

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'post'
        ordering = ['-created_at']
        verbose_name = '포스트'
        verbose_name_plural = '포스트 목록'


class Comment(models.Model):
    id = models.AutoField(primary_key=True)
    author = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, verbose_name='로그인한 작성자')
    author_name = models.CharField(max_length=50, blank=True, verbose_name='익명 작성자')
    content = models.TextField(verbose_name='내용')
    password = models.CharField(max_length=128, null=True, blank=False, default=make_password('1111'), verbose_name='익명 비밀번호')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name='게시글')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    def __str__(self):
        return f'Comment by {self.author.username} on Post {self.post.id}'

    class Meta:
        db_table = 'comment'
        ordering = ['-created_at']
        verbose_name = '댓글'
        verbose_name_plural = '댓글 목록'

    # 로그인한 사용자의 경우 author_name 비워둠
    def save(self, *args, **kwargs):
        if self.author:
            self.author_name = ''
        super().save(*args, **kwargs)

