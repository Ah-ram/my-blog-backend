from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.conf import settings

from .models import Post, Comment

User = get_user_model()

class PostViewSetTest(APITestCase):
    NUM_POSTS = 4000

    def setUp(self):
        self.client = APIClient()
        # 테스트 환경에서 쿼리 로깅 활성화
        settings.DEBUG = True

        self.admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'password')
        self.user = User.objects.create_user('user', 'user@test.com', 'password')

        for i in range(self.NUM_POSTS):
            author = self.admin_user if i % 2 == 0 else self.user
            post = Post.objects.create(
                author=author,
                title=f'Test Post #{i}',
                content=f'Test Content #{i}',
            )
            post.tags.add(f'tag{i}', 'django')
            # self.comment = Comment.objects.create(post=self.post, author=self.admin_user, content='Test Comment')

    def measure_performance(self, url, num_runs=3):
        '''
        성능 측정 반복 로직
        '''
        total_time = 0
        num_queries = 0

        for i in range(num_runs):
            connection.queries.clear()

            start_time = time.time()
            response = self.client.get(url)
            end_time = time.time()

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            elapsed_time = end_time - start_time
            total_time += elapsed_time

            # 쿼리 수 기록 (마지막 반복의 쿼리 수를 대표값을 사용)
            num_queries = len(connection.queries)
            print(f' 반복 {i+1}: 소요시간 {elapsed_time:.4f}s / 쿼리 수 {num_queries}개')

        average_time = total_time / num_runs

        # 실제 데이터 검증 (결과 개수)
        self.assertEqual(len(response.data), self.NUM_POSTS)

        return average_time, num_queries


    # def test_list_posts_pre_optimization(self):
    #     """
    #     [최적화 전] 게시물 목록 조회 성능 측정.
    #     N=8000일 때, 1(목록) + 8000(작성자) + 8000(태그) = 약 16,001개 쿼리가 발생해야 합니다
    #     """
    #     url = reverse('post-list')
    #
    #     print("\n\n--- 🚀 게시물 목록 최적화 전 성능 측정 시작  ---")
    #
    #     average_time, num_queries = self.measure_performance(url, num_runs=3)
    #     print("\n--- ✨ 측정 결과 (최적화 전 기준 지표) ---")
    #     print(f"1. 게시글 수: 4000개")
    #     print(f"2. 응답 시간 (1회): {average_time:.4f}초")
    #     print(f"3. 쿼리 수: {num_queries}개")
    #     print("--------------------------------------------------")
    #
    #     self.assertGreaterEqual(num_queries, 7000,
    #                             msg=f"N+1 쿼리 문제 검증 실패. 쿼리 수가 너무 적습니다: {num_queries}개")

    def test_list_posts_post_optimization(self):
        """
        [최적화 후] 게시물 목록 조회 성능 측정 및 개선 효과 검증
        쿼리 수가 5개 이하로 줄어야 합니다.
        """
        url = reverse('post-list')

        print("\n\n--- ✅ 게시물 목록 최적화 후 성능 측정 시작  ---")

        average_time, num_queries = self.measure_performance(url, num_runs=3)
        print("\n--- ✨ 측정 결과 (최적화 후 지표) ---")
        print(f"1. 게시글 수: {self.NUM_POSTS}개")
        print(f"2. 응답 시간 (평균): {average_time:.4f}초")
        print(f"3. 쿼리 수: {num_queries}개")
        print("--------------------------------------------------")

        # 최적화된 쿼리셋은 쿼리 수가 5개 이하(JOIN 1 + PREFETCH 1 + 기타 2~3)여야 합니다.
        self.assertLessEqual(num_queries, 5,
                             msg=f'쿼리 최적화가 적용되지 않았거나 비효율적입니다. 쿼리수: {num_queries}개')

    # def test_retrieve_post(self):
    #     """
    #     Ensure any user can retrieve a post.
    #     """
    #     url = reverse('post-detail', kwargs={'pk': self.post.pk})
    #     import time
    #     start = time.time()
    #     response = self.client.get(url)
    #     print(f'소요 시간: {time.time()-start:.5f}s')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(response.data['title'], self.post.title)
    #
    # def test_create_post_by_admin(self):
    #     """
    #     Ensure admin user can create a post.
    #     """
    #     self.client.login(username='admin', password='password')
    #     url = reverse('post-list')
    #     data = {'title': 'New Post by Admin', 'content': 'Content'}
    #     response = self.client.post(url, data)
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     self.assertEqual(Post.objects.count(), 2)
    #
    # def test_create_post_by_non_admin(self):
    #     """
    #     Ensure non-admin user cannot create a post.
    #     """
    #     self.client.login(username='user', password='password')
    #     url = reverse('post-list')
    #     data = {'title': 'New Post by User', 'content': 'Content'}
    #     response = self.client.post(url, data)
    #     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    #
    # def test_update_post_by_author(self):
    #     """
    #     Ensure the author can update their post.
    #     """
    #     self.client.login(username='admin', password='password')
    #     url = reverse('post-detail', kwargs={'pk': self.post.pk})
    #     data = {'title': 'Updated Title'}
    #     response = self.client.patch(url, data)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.post.refresh_from_db()
    #     self.assertEqual(self.post.title, 'Updated Title')
    #
    # def test_delete_post_by_author(self):
    #     """
    #     Ensure the author can delete their post.
    #     """
    #     self.client.login(username='admin', password='password')
    #     url = reverse('post-detail', kwargs={'pk': self.post.pk})
    #     response = self.client.delete(url)
    #     self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    #     self.assertEqual(Post.objects.count(), 0)


class CommentViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('user', 'user@test.com', 'password')
        self.post = Post.objects.create(author=self.user, title='Test Post', content='Test Content')
        self.comment = Comment.objects.create(post=self.post, author=self.user, content='Test comment')

    def test_create_comment_authenticated(self):
        """
        Ensure authenticated user can create a comment.
        """
        self.client.login(username='user', password='password')
        url = reverse('post-comments-list')
        data = {'post_id': self.post.pk, 'content': 'New comment'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 2)

    def test_create_comment_anonymous(self):
        """
        Ensure anonymous user can create a comment with a password.
        """
        url = reverse('post-comments-list')
        data = {'post_id': self.post.pk, 'content': 'Anonymous comment', 'password': 'anonpassword'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 2)
        new_comment = Comment.objects.get(id=response.data['id'])
        self.assertIsNone(new_comment.author)
        self.assertTrue(new_comment.check_password('anonpassword'))

    def test_update_comment_by_author(self):
        """
        Ensure comment author can update their comment.
        """
        self.client.login(username='user', password='password')
        url = reverse('post-comments-detail', kwargs={'pk': self.comment.pk})
        data = {'content': 'Updated comment'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, 'Updated comment')

    def test_delete_comment_by_author(self):
        """
        Ensure comment author can delete their comment.
        """
        self.client.login(username='user', password='password')
        url = reverse('post-comments-detail', kwargs={'pk': self.comment.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Comment.objects.count(), 0)

    def test_update_anonymous_comment_with_correct_password(self):
        """
        Ensure anonymous comment can be updated with the correct password.
        """
        anon_comment = Comment.objects.create(post=self.post, content='Anon to update', password='testpassword')
        url = reverse('post-comments-detail', kwargs={'pk': anon_comment.pk})
        data = {'content': 'Updated anon comment', 'password': 'testpassword'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        anon_comment.refresh_from_db()
        self.assertEqual(anon_comment.content, 'Updated anon comment')

    def test_update_anonymous_comment_with_incorrect_password(self):
        """
        Ensure anonymous comment cannot be updated with an incorrect password.
        """
        anon_comment = Comment.objects.create(post=self.post, content='Anon to fail update', password='testpassword')
        url = reverse('post-comments-detail', kwargs={'pk': anon_comment.pk})
        data = {'content': 'Updated anon comment', 'password': 'wrongpassword'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_anonymous_comment_with_correct_password(self):
        """
        Ensure anonymous comment can be deleted with the correct password.
        """
        anon_comment = Comment.objects.create(post=self.post, content='Anon to delete', password='testpassword')
        url = reverse('post-comments-detail', kwargs={'pk': anon_comment.pk})
        data = {'password': 'testpassword'}
        response = self.client.delete(url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(pk=anon_comment.pk).exists())

    def test_get_comments_for_post(self):
        """
        Ensure comments for a specific post can be retrieved.
        """
        url = reverse('post-comments', kwargs={'pk': self.post.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['content'], self.comment.content)


from django.db import connection   # 쿼리 수 측정을 위해 추가
import time

class PreOptimizationPerformanceTest(APITestCase):
    """
    쿼리 최적화 전 N+1 쿼리 문제를 유발하여 성능 측정의 기준 지표를 설정하는 테스트입니다.
    """
    def setUp(self):
        settings.DEBUG = True

        self.client = APIClient()
        self.user = User.objects.create_user('perf_user', 'perf@test.com', 'password')
        self.admin_user = User.objects.create_superuser('perf_admin', 'perf_admin@test.com', 'password')
        self.post = Post.objects.create(
            author=self.admin_user,
            title='Perf Post',
            content='Test content for performance')

        # N+1 쿼리를 유발하기 위한 댓글 생성
        for i in range(8000):
            Comment.objects.create(
                post=self.post,
                author=self.user,    # 작성자를 일반 사용자로 지정(쿼리 복잡성 증가)
                content=f'Test Comment {i}'
            )

    def test_retrieve_post_performance_pre_optimization(self):
        """
        [최적화 전] 게시물 상세 조회 API의 평균 응답 시간과 쿼리 수를 측정합니다.
        (N+1 쿼리가 발생하는 상태 가정)
        """
        total_time = 0

        url = reverse('post-get-comments-list', kwargs={'pk': self.post.pk})

        print("\n\n--- 🚀 쿼리 최적화 전 성능 측정 시작 ---")

        for i in range(5):
            # 매번 쿼리 로깅을 초기화하여 해당 요청에 대한 쿼리만 측정
            connection.queries.clear()

            start_time = time.time()
            response = self.client.get(url)
            end_time = time.time()

            # API 요청 성공 확인
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            elapsed_time = end_time - start_time
            total_time += elapsed_time

            # 쿼리 수 기록
            num_queries = len(connection.queries)
            print(f' 반복 {i+1}: 소요 시간 {elapsed_time: .4f}s / 쿼리 수 {num_queries}개')

        average_time = total_time / 5

        print("\n--- ✨ 측정 결과 (최적화 전 기준 지표) ---")
        print(f"1. 댓글 수: 8000개")
        print(f"2. 평균 응답 시간 (5회): {average_time:.4f}초")
        print(f"3. 쿼리 수: {num_queries}개")
        print("--------------------------------------------------")

        # T_before (최적화 전 시간)을 기록함
        self.pre_optimization_time = average_time


    def test_retrieve_post_performance_post_optimization(self):
        """
        [최적화 후] 게시물 댓글 목록 조회 API의 성능을 측정하고 개선 효과를 검증합니다.
        :return: select_related 적용으로 쿼리 수가 5개 이하로 줄어야 함
        """
        total_time = 0

        url = reverse('post-get-comments-list', kwargs={'pk': self.post.pk})

        print("\n\n--- ✅ 쿼리 최적화 후 성능 측정 시작 ---")

        for i in range(5):
            # 쿼리 로그를 비워 해당 요청에 대한 쿼리만 측정
            connection.queries.clear()

            start_time = time.time()
            response = self.client.get(url)
            end_time = time.time()

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            elapsed_time = end_time - start_time
            total_time += elapsed_time

            num_queries = len(connection.queries)
            print(f' 반복 {i+1}: 소요 시간 {elapsed_time: .4f}s / 쿼리 수 {num_queries}개')

        average_time = total_time / 5

        print("\n--- ✨ 측정 결과 (최적화 후 지표) ---")
        print(f"1. 댓글 수: 8000개")
        print(f"2. 평균 응답 시간 (5회): {average_time:.4f}초")
        print(f"3. 쿼리 수: {num_queries}개")
        print("--------------------------------------------------")

        self.post_optimization_time = average_time
        # 쿼리 수가 5개 이하로 줄었는지 검증
        self.assertLessEqual(num_queries, 5,
                             msg=f'쿼리 최적화가 적용되지 않았거나 비효율적입니다. 쿼리 수 : {num_queries}개')


            