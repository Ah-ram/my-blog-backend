from django.contrib import admin
from .models import Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'updated_at')
    list_filter = ('created_at', 'author__username')
    search_fields = ('title', 'content', 'tags__name')
    raw_id_fields = ('author',)   # author 필드를 ID로 직접 입력하여 검색가능
    date_hierarchy = 'created_at'  # 날짜 계층 구조 필터링
    ordering = ('-created_at',)

    # 새로운 Post 객체 저장 시 author 필드를 현재 로그인한 사용자로 자동 설정
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return request.user and request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff





