import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class GithubOAuthRedirect(APIView):
    '''
    Github 로그인 페이지로 리다이렉트할 URL을 프론트엔드에 반환
    '''
    permission_classes = []

    def get(self, request):
        github_auth_url = (
            f'https://github.com/login/oauth/authorize?'
            f'client_id={settings.GITHUB_CLIENT_ID}&'
            f'redirect_url={settings.GITHUB_CALLBACK_URL}&'
            f'scope=read:user,user:email'
        )

        return Response({'github_auth_url': github_auth_url}, status=status.HTTP_200_OK)


class GithubLogin(APIView):
    '''
    프론트엔드로부터 인증 코드를 받아 JWT 토큰을 JSON으로 반환
    '''
    permission_classes = []

    def post(self, request):
        code = request.data.get('code')
        print(code)

        if not code:
            return Response({'error': 'Authorization code not provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Github에 AccessToken 요청
        token_url = (f'https://github.com/login/oauth/access_token?code={code}'
                     f'&client_id={settings.GITHUB_CLIENT_ID}'
                     f'&client_secret={settings.GITHUB_CLIENT_SECRET}')
        token_headers = {'Accept': 'application/json'}

        try:
            token_response = requests.post(token_url, headers=token_headers)
            print(token_response.json())
            token_response.raise_for_status()
            token_json = token_response.json()

            print(token_json)
        except requests.exceptions.RequestException as e:
            return Response({'error': f'Failed to get access token from Github: {e}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if 'error' in token_json:
            return Response(token_json, status=status.HTTP_400_BAD_REQUEST)

        access_token = token_json.get('access_token')

        if not access_token:
            return Response({'error': 'Access token not received from Github'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Github API로 사용자 정보 요청
        user_info_url = 'https://api.github.com/user'
        user_info_headers = {'Authorization': f'Bearer {access_token}'}

        try:
            user_info_response = requests.get(user_info_url, headers=user_info_headers)
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
        except requests.exceptions.RequestException as e:
            return Response({'error': f'Failed to fetch user info from Github: {e}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not user_info:
            return Response({'error': 'Could not fetch user info from Github'},
                            status=status.HTTP_400_BAD_REQUEST)

        github_id = str(user_info.get('id'))
        github_username = user_info.get('login')
        github_email = user_info.get('email')

        if not github_email:
            emails_url = 'https://api.github.com/user/emails'

            try:
                emails_response = requests.get(emails_url, headers=user_info_headers)
                emails_response.raise_for_status()
                emails = emails_response.json()

                for email in emails:
                    if email.get('primary') and email.get('verified'):
                        github_email = email.get('email')
                        break

            except requests.exceptions.RequestException as e:
                print(f'Warning: Counld not fetch emails from Github: {e}')

        if not github_email:
            github_email = f'{github_username}@github.com'

        # 사용자 존재 여부 확인 및 생성/업데이트
        try:
            user = User.objects.get(github_id=github_id)

            if user.username != github_username:
                user.username = github_username
                user.nickname = github_username
            if user.email != github_email:
                user.email = github_email
            user.save()
        except User.DoesNotExist:
            user = User.objects.create(
                username=github_username,
                nickname=github_username,
                email=github_email,
                github_id=github_id,
            )
            user.set_unusable_password()
            user.save()

        # JWT 토큰 발급
        refresh = RefreshToken.for_user(user)

        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user_info': {
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
            }
        }, status=status.HTTP_200_OK)
