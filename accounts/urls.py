from django.urls import path
from .views import GithubOAuthRedirect, GithubLogin
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView)

urlpatterns = [
    path('github/', GithubOAuthRedirect.as_view(), name='github_oauth_redirect'),
    path('github/login/', GithubLogin.as_view(), name='github_login'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]