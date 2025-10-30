import os
import uuid

from botocore.exceptions import ClientError
from django.contrib.admin.templatetags.admin_list import pagination
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render

from rest_framework import viewsets, permissions, status, exceptions
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.views import APIView

from .models import Post, Comment
from .serializers import PostSerializer, CommentSerializer
from .utils import generate_s3_presigned_url, resize_image_and_upload_to_s3, \
    delete_unused_images, move_temp_images_to_final_location


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().select_related('author').prefetch_related('tags')
    serializer_class = PostSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tags__name']
    search_fields = ['title', 'tags__name', 'author__nickname']
    ordering_fields = ['created_at', 'title']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAdminUser]
        else:
            self.permission_classes = [permissions.AllowAny]
        return [permission() for permission in self.permission_classes]

    def list(self, request, *args, **kwargs):
        self.pagination_class = None

        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        content = serializer.validated_data.get('content', '')
        final_content = move_temp_images_to_final_location(content)

        serializer.save(author=self.request.user, content=final_content)

    def perform_update(self, serializer):
        if self.request.user != serializer.instance.author:
            self.permission_denied(self.request, message='게시글 수정 권한이 없습니다.')

        old_content = self.get_object().content
        new_content = self.request.data.get('content', '')

        final_content = move_temp_images_to_final_location(new_content)

        serializer.save(content=final_content)

        if old_content and final_content:
            delete_unused_images(old_content, final_content)

    def perform_destroy(self, instance):
        if self.request.user != instance.author:
            self.permission_denied(self.request, message='게시글 삭제 권한이 없습니다.')

        post_content = instance.content
        instance.delete()

        if post_content:
            delete_unused_images(post_content, '')

    @action(detail=True, methods=['GET'], url_path='comments')
    def get_comments_list(self, request, pk=None):
        comments_list = Comment.objects.filter(post=pk)
        # pagination = PageNumberPagination()
        # page = pagination.paginate_queryset(comments_list, request)
        # page = self.paginate_queryset(comments_list)
        # serializer = CommentSerializer(page, many=True)
        serializer = CommentSerializer(comments_list, many=True)
        # return self.get_paginated_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class S3PresignedURLView(APIView):
    permission_classes = [AllowAny]
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 50MB(52428800)

    def post(self, request):
        file_name = request.data.get('file_name')
        file_type = request.data.get('file_type')
        file_size = request.data.get('file_size')

        if not file_name or not file_type or not file_size:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"error": "file_name, file_type, file_size는 필수입니다."})

        if file_size > self.MAX_UPLOAD_SIZE:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': '파일 크기는 50MB를 초과할 수 없습니다.'})

        if not file_type.startswith('image/'):
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': '이미지 파일만 업로드할 수 있습니다.'})

        try:
            urls = generate_s3_presigned_url(file_name, file_type)

            return Response(urls, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={"error": str(e)})


class ImageUploadView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s3_key = request.data.get('s3_key')

        if s3_key is None:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': 's3_key가 누락되었습니다.'})

        try:
            image_url = resize_image_and_upload_to_s3(s3_key)

            if not image_url:
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                data={'error': '리사이즈된 이미지 업로드에 실패했습니다.'})

            return Response(image_url, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            data={'error': str(e)})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        post_id = self.request.data.get('post_id')
        post = Post.objects.get(id=post_id)
        password = self.request.data.get('password')

        if self.request.user.is_authenticated:
            serializer.save(
                author=self.request.user,
                password=None,
                post=post)
        else:
            nickname = f'user_{uuid.uuid4().hex[:8]}'
            serializer.save(
                author=None,
                author_name=nickname,
                password=make_password(password),
                post=post
            )

    def perform_update(self, serializer):
        if not self.request.user.is_authenticated:
            password = self.request.data.get('password')

            if not password:
                raise exceptions.PermissionDenied(detail='익명 댓글 수정 시 비밀번호를 입력해야 합니다.')

            if not check_password(password, serializer.instance.password):
                raise exceptions.PermissionDenied(detail='비밀번호가 일치하지 않습니다.')

            serializer.save()

        elif self.request.user != serializer.instance.author:
            raise exceptions.PermissionDenied(detail='댓글 수정 권한이 없습니다.')
        else:
            serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_authenticated:
            password = self.request.data.get('password')

            if not password:
                raise exceptions.PermissionDenied(detail='익명 댓글 삭제 시 비밀번호를 입력해야 합니다.')

            if not check_password(password, instance.password):
                raise exceptions.PermissionDenied(detail='비밀번호가 일치하지 않습니다.')

            instance.delete()

        elif self.request.user != instance.author:
            if not self.request.user.is_staff:
                raise exceptions.PermissionDenied(detail='댓글 삭제 권한이 없습니다.')
            instance.delete()
        else:
            instance.delete()