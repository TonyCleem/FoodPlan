from django.contrib import admin
from django.utils.html import format_html
from .models import Recipe, Ingredient, UserProfile


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
  list_display = ('name', 'calories', 'is_vegetarian', 'diet_type', 'dish_type',
                 'no_gluten', 'total_cost', 'like_count', 'image_preview')
  list_filter = ('is_vegetarian', 'diet_type', 'dish_type', 'no_gluten',
                 'created_at')
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
  list_display = ('user', 'allergies', 'liked_recipes_count')
  filter_horizontal = ('liked_recipes',)
  search_fields = ('user__username', 'user__email', 'allergies')
  list_filter = ('user__is_active',)

  def liked_recipes_count(self, obj):
    return obj.liked_recipes.count()
  liked_recipes_count.short_description = 'Количество лайкнутых рецептов'