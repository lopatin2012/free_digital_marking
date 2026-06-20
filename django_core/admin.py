from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import mark_safe

from app_true_api.models import UserProfile


# ============================================
# Расширение стандартной админки User
# ============================================

class UserProfileInlineForUser(admin.StackedInline):
    """Инлайн профиля в админке пользователя"""
    model = UserProfile
    can_delete = False
    verbose_name = 'Привязка к организации'
    verbose_name_plural = 'Привязка к организации'


class CustomUserAdmin(BaseUserAdmin):
    """Расширенная админка пользователей"""
    inlines = [UserProfileInlineForUser]
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'get_organization', 'is_staff', 'is_active'
    )
    list_select_related = ('profile', 'profile__organization')

    def get_organization(self, obj):
        """Отображает организацию пользователя"""
        if hasattr(obj, 'profile') and obj.profile.organization:
            return obj.profile.organization.name
        return mark_safe('<span style="color: gray;">Не указана</span>')

    get_organization.short_description = 'Организация'


# Перерегистрируем User
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# ============================================
# Настройки админ-панели
# ============================================

admin.site.site_header = 'Система маркировки'
admin.site.site_title = 'Администрирование'
