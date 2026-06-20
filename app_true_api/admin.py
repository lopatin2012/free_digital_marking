from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html, mark_safe

from app_true_api.models import (
    Organization,
    UserProfile,
    ElectronicDigitalSignature,
    DeviceSUZ,
)

# ============================================
# Inline классы для вложенного редактирования
# ============================================

class UserProfileInline(admin.StackedInline):
    """Профили пользователей внутри организации"""
    model = UserProfile
    extra = 0
    verbose_name = 'Профиль пользователя'
    verbose_name_plural = 'Профили пользователей'
    autocomplete_fields = ['user']


class ElectronicDigitalSignatureInline(admin.StackedInline):
    """ЭЦП внутри организации"""
    model = ElectronicDigitalSignature
    extra = 0
    verbose_name = 'Электронная цифровая подпись'
    verbose_name_plural = 'Электронные цифровые подписи'
    fields = (
        'name', 'serial_number', 'is_active',
        'valid_from', 'valid_to',
        'activation_date', 'deactivation_date'
    )
    readonly_fields = ('activation_date', 'deactivation_date')


class DeviceSUZInline(admin.StackedInline):
    """Устройства СУЗ внутри организации"""
    model = DeviceSUZ
    extra = 0
    verbose_name = 'Устройство СУЗ'
    verbose_name_plural = 'Устройства СУЗ'
    fields = (
        'name', 'oms_id', 'connection_id', 'is_active',
        'current_dynamic_token', 'token_is_valid_until'
    )
    readonly_fields = ('current_dynamic_token', 'token_is_valid_until')


# ============================================
# Основные ModelAdmin классы
# ============================================

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Админка организаций"""
    list_display = ('name', 'inn', 'active_eds_count', 'active_suz_count', 'users_count')
    search_fields = ('name', 'inn')
    list_filter = ('name',)
    inlines = [UserProfileInline, ElectronicDigitalSignatureInline, DeviceSUZInline]

    @admin.display(description='Активных ЭЦП')
    def active_eds_count(self, obj):
        """Количество активных ЭЦП"""
        count = obj.eds_settings.filter(is_active=True).count()
        color = 'green' if count == 1 else 'red'
        return mark_safe(
            str.format(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, count
            )
        )

    active_eds_count.short_description = 'Активных ЭЦП'

    def active_suz_count(self, obj):
        """Количество активных СУЗ"""
        count = obj.suz_devices.filter(is_active=True).count()
        color = 'green' if count == 1 else 'red'
        return mark_safe(
            str.format(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, count
            )
        )

    active_suz_count.short_description = 'Активных СУЗ'

    def users_count(self, obj):
        """Количество пользователей"""
        return obj.user_profiles.count()

    users_count.short_description = 'Пользователей'


@admin.register(ElectronicDigitalSignature)
class ElectronicDigitalSignatureAdmin(admin.ModelAdmin):
    """Админка ЭЦП"""
    list_display = (
        'name', 'organization', 'serial_number',
        'is_active_badge', 'validity_badge',
        'valid_from', 'valid_to'
    )
    list_filter = ('is_active', 'organization')
    search_fields = ('name', 'serial_number', 'organization__name')
    autocomplete_fields = ['organization']
    readonly_fields = ('activation_date', 'deactivation_date')

    fieldsets = (
        ('Основная информация', {
            'fields': ('organization', 'name', 'serial_number')
        }),
        ('Статус', {
            'fields': ('is_active', 'activation_date', 'deactivation_date')
        }),
        ('Срок действия', {
            'fields': ('valid_from', 'valid_to')
        }),
    )

    def is_active_badge(self, obj):
        """Красивый бейдж активности"""
        if obj.is_active:
            return mark_safe(
                '<span style="background: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 10px; font-size: 11px;">АКТИВНА</span>'
            )
        return mark_safe(
            '<span style="background: #dc3545; color: white; padding: 3px 10px; '
            'border-radius: 10px; font-size: 11px;">НЕАКТИВНА</span>'
        )

    is_active_badge.short_description = 'Статус'
    is_active_badge.admin_order_field = 'is_active'

    def validity_badge(self, obj):
        """Бейдж валидности по времени"""
        if obj.is_valid_now:
            return mark_safe(
                '<span style="color: green;">✓ Действительна</span>'
            )
        return mark_safe(
            '<span style="color: red;">✗ Недействительна</span>'
        )

    validity_badge.short_description = 'Валидна'


@admin.register(DeviceSUZ)
class DeviceSUZAdmin(admin.ModelAdmin):
    """Админка устройств СУЗ"""
    list_display = (
        'name', 'organization', 'oms_id', 'connection_id',
        'is_active_badge', 'token_status', 'token_is_valid_until'
    )
    list_filter = ('is_active', 'organization')
    search_fields = ('name', 'oms_id', 'connection_id', 'organization__name')
    autocomplete_fields = ['organization']

    fieldsets = (
        ('Основная информация', {
            'fields': ('organization', 'name', 'oms_id', 'connection_id', 'is_active')
        }),
        ('Токен', {
            'fields': ('current_dynamic_token', 'token_is_valid_until'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('current_dynamic_token', 'token_is_valid_until')

    def is_active_badge(self, obj):
        """Красивый бейдж активности"""
        if obj.is_active:
            return mark_safe(
                '<span style="background: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 10px; font-size: 11px;">АКТИВНО</span>'
            )
        return mark_safe(
            '<span style="background: #dc3545; color: white; padding: 3px 10px; '
            'border-radius: 10px; font-size: 11px;">НЕАКТИВНО</span>'
        )

    is_active_badge.short_description = 'Статус'
    is_active_badge.admin_order_field = 'is_active'

    def token_status(self, obj):
        """Статус токена"""
        if not obj.current_dynamic_token:
            return mark_safe('<span style="color: gray;">Нет токена</span>')

        if obj.is_token_valid:
            return mark_safe('<span style="color: green;">✓ Валиден</span>')
        return mark_safe('<span style="color: red;">✗ Истёк</span>')

    token_status.short_description = 'Токен'

    actions = ['invalidate_tokens']

    @admin.action(description='Сбросить токены выбранных устройств')
    def invalidate_tokens(self, request, queryset):
        """Сбрасывает токены для выбранных устройств"""
        updated = queryset.update(
            current_dynamic_token='',
            token_is_valid_until=timezone.now()
        )
        self.message_user(request, f'Токены сброшены для {updated} устройств.')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Админка профилей пользователей"""
    list_display = ('user', 'organization', 'user_email', 'user_is_active')
    list_filter = ('organization',)
    search_fields = ('user__username', 'user__email', 'organization__name')
    autocomplete_fields = ['user', 'organization']

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = 'Email'

    def user_is_active(self, obj):
        return obj.user.is_active

    user_is_active.short_description = 'Активен'
    user_is_active.boolean = True

