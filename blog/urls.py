from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import PostViewSet, S3PresignedURLView, ImageUploadView, CommentViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet)

# comments_router = routers.NestedSimpleRouter(router, r'posts', lookup='post')
router.register(r'comments', CommentViewSet, basename='post-comments')

urlpatterns = [
    path('', include(router.urls)),
    path('s3-presigned-url/', S3PresignedURLView.as_view(), name='s3-presigned-url'),
    path('image-upload/', ImageUploadView.as_view(), name='image-upload'),
]
urlpatterns += router.urls
