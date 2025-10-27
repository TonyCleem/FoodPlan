from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Recipe, Ingredient, UserProfile


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
  list_display = ('name', 'calories', 'is_vegetarian', 'diet_type', 'dish_type',
                 'no_gluten', 'total_cost', 'like_count', 'image_preview', 'meal_type')
  list_filter = ('is_vegetarian', 'diet_type', 'dish_type', 'no_gluten',
                 'created_at', 'meal_type')
  search_fields = ('name',)
  filter_horizontal = ('ingredients',)
  list_editable = ('is_vegetarian', 'no_gluten')
  ordering = ('-created_at',)
  date_hierarchy = 'created_at'
  actions = ['make_vegetarian', 'make_non_vegetarian', 'make_gluten_free',
             'make_non_gluten_free']

  def like_count(self, obj):
    return obj.liked_by.count()
  like_count.short_description = 'Количество лайков'

  def image_preview(self, obj):
    if obj.image:
      return format_html('<img src="{}" style="max-height: 50px;" />',
                        obj.image.url)
    return 'Нет изображения'
  image_preview.short_description = 'Превью'

  def make_vegetarian(self, request, queryset):
    queryset.update(is_vegetarian=True)
  make_vegetarian.short_description = 'Пометить как вегетарианское'

  def make_non_vegetarian(self, request, queryset):
    queryset.update(is_vegetarian=False)
  make_non_vegetarian.short_description = 'Пометить как невегетарианское'

  def make_gluten_free(self, request, queryset):
    queryset.update(no_gluten=True)
  make_gluten_free.short_description = 'Пометить как безглютеновое'

  def make_non_gluten_free(self, request, queryset):
    queryset.update(no_gluten=False)
  make_non_gluten_free.short_description = 'Пометить как содержащее глютен'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
  list_display = ('name', 'weight', 'cost')
  search_fields = ('name',)
  list_editable = ('weight', 'cost')
  ordering = ('name',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'allergies',
        'liked_recipes_count',
        'disliked_recipes_count',
        'breakfast_status_display',
        'lunch_status_display',
        'dinner_status_display',
        'last_refresh_date_display'
    )
    filter_horizontal = ('liked_recipes', 'disliked_recipes')
    search_fields = ('user__username', 'user__email', 'allergies')
    list_filter = ('user__is_active',)
    actions = [
        'reset_all_limits',
        'reset_breakfast_limits',
        'reset_lunch_limits',
        'reset_dinner_limits',
        'clear_disliked_recipes',
        'clear_liked_recipes'
    ]
    readonly_fields = ('last_refresh_date', 'breakfast_blocked_until', 'lunch_blocked_until', 'dinner_blocked_until')

    def liked_recipes_count(self, obj):
        return obj.liked_recipes.count()
    liked_recipes_count.short_description = 'Лайкнутые'

    def disliked_recipes_count(self, obj):
        return obj.disliked_recipes.count()
    disliked_recipes_count.short_description = 'Дизлайкнутые'

    def last_refresh_date_display(self, obj):
        return obj.last_refresh_date.strftime('%d.%m.%Y %H:%M')
    last_refresh_date_display.short_description = 'Последнее обновление'

    def breakfast_status_display(self, obj):
        obj.reset_refresh_counts()
        if obj.breakfast_blocked_until and timezone.now() < obj.breakfast_blocked_until:
            return f"🚫 До {obj.breakfast_blocked_until.strftime('%d.%m.%Y %H:%M')}"
        remaining = 3 - obj.breakfast_refresh_count
        return f"✅ {obj.breakfast_refresh_count}/3 (ост: {remaining})"
    breakfast_status_display.short_description = 'Завтрак'

    def lunch_status_display(self, obj):
        obj.reset_refresh_counts()
        if obj.lunch_blocked_until and timezone.now() < obj.lunch_blocked_until:
            return f"🚫 До {obj.lunch_blocked_until.strftime('%d.%m.%Y %H:%M')}"
        remaining = 3 - obj.lunch_refresh_count
        return f"✅ {obj.lunch_refresh_count}/3 (ост: {remaining})"
    lunch_status_display.short_description = 'Обед'

    def dinner_status_display(self, obj):
        obj.reset_refresh_counts()
        if obj.dinner_blocked_until and timezone.now() < obj.dinner_blocked_until:
            return f"🚫 До {obj.dinner_blocked_until.strftime('%d.%m.%Y %H:%M')}"
        remaining = 3 - obj.dinner_refresh_count
        return f"✅ {obj.dinner_refresh_count}/3 (ост: {remaining})"
    dinner_status_display.short_description = 'Ужин'

    def reset_all_limits(self, request, queryset):
        for profile in queryset:
            profile.breakfast_refresh_count = 0
            profile.lunch_refresh_count = 0
            profile.dinner_refresh_count = 0
            profile.breakfast_blocked_until = None
            profile.lunch_blocked_until = None
            profile.dinner_blocked_until = None
            profile.last_refresh_date = timezone.now()
            profile.save()
        self.message_user(request, "Все лимиты сброшены")
    reset_all_limits.short_description = "Сбросить все лимиты"

    def reset_breakfast_limits(self, request, queryset):
        for profile in queryset:
            profile.breakfast_refresh_count = 0
            profile.breakfast_blocked_until = None
            profile.last_refresh_date = timezone.now()
            profile.save()
        self.message_user(request, "Лимиты завтрака сброшены")
    reset_breakfast_limits.short_description = "Сбросить лимиты завтрака"

    def reset_lunch_limits(self, request, queryset):
        for profile in queryset:
            profile.lunch_refresh_count = 0
            profile.lunch_blocked_until = None
            profile.last_refresh_date = timezone.now()
            profile.save()
        self.message_user(request, "Лимиты обеда сброшены")
    reset_lunch_limits.short_description = "Сбросить лимиты обеда"

    def reset_dinner_limits(self, request, queryset):
        for profile in queryset:
            profile.dinner_refresh_count = 0
            profile.dinner_blocked_until = None
            profile.last_refresh_date = timezone.now()
            profile.save()
        self.message_user(request, "Лимиты ужина сброшены")
    reset_dinner_limits.short_description = "Сбросить лимиты ужина"

    def clear_disliked_recipes(self, request, queryset):
        for profile in queryset:
            profile.disliked_recipes.clear()
            profile.save()
        self.message_user(request, "Дизлайкнутые рецепты очищены")
    clear_disliked_recipes.short_description = "Очистить дизлайкнутые рецепты"

    def clear_liked_recipes(self, request, queryset):
        for profile in queryset:
            profile.liked_recipes.clear()
            profile.save()
        self.message_user(request, "Лайкнутые рецепты очищены")
    clear_liked_recipes.short_description = "Очистить лайкнутые рецепты"

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'allergies', 'filters')
        }),
        ('Рецепты', {
            'fields': ('liked_recipes', 'disliked_recipes')
        }),
        ('Лимиты обновлений', {
            'fields': (
                'breakfast_refresh_count',
                'lunch_refresh_count',
                'dinner_refresh_count',
                'last_refresh_date'
            )
        }),
        ('Блокировки (автоматические)', {
            'fields': (
                'breakfast_blocked_until',
                'lunch_blocked_until',
                'dinner_blocked_until'
            )
        }),
    )