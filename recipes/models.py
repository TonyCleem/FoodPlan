from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Ingredient(models.Model):
  name = models.CharField(max_length=100, verbose_name='Название')
  weight = models.FloatField(verbose_name='Вес (г)')
  cost = models.DecimalField(max_digits=10, decimal_places=2,
                            verbose_name='Стоимость (₽)')

  def __str__(self):
    return f"{self.name} ({self.weight}г, {self.cost}₽)"

  class Meta:
    verbose_name = 'Ингредиент'
    verbose_name_plural = 'Ингредиенты'


class Recipe(models.Model):
  DIET_CHOICES = [
    ('low_calorie', 'Низкокалорийное'),
    ('regular', 'Обычное'),
  ]
  TYPE_CHOICES = [
    ('fish', 'Рыба и морепродукты'),
    ('meat', 'Мясо'),
    ('grains', 'Зерновые'),
    ('honey', 'Продукты пчеловодства'),
    ('nuts', 'Орехи и бобовые'),
    ('dairy', 'Молочные продукты'),
  ]
  name = models.CharField(max_length=200, verbose_name='Название')
  image = models.ImageField(upload_to='recipes/', null=True, blank=True,
                           verbose_name='Изображение')
  ingredients = models.ManyToManyField(Ingredient, related_name='recipes',
                                      verbose_name='Ингредиенты')
  calories = models.IntegerField(verbose_name='Калорийность (ккал)')
  is_vegetarian = models.BooleanField(default=False, verbose_name='Вегетарианское')
  diet_type = models.CharField(max_length=20, choices=DIET_CHOICES,
                               default='regular', verbose_name='Тип диеты')
  dish_type = models.CharField(max_length=20, choices=TYPE_CHOICES,
                              verbose_name='Тип блюда')
  no_gluten = models.BooleanField(default=False, verbose_name='Без глютена')
  created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

  def total_cost(self):
    return sum(ingredient.cost for ingredient in self.ingredients.all())

  def __str__(self):
    return self.name

  class Meta:
    verbose_name = 'Рецепт'
    verbose_name_plural = 'Рецепты'


class UserProfile(models.Model):
  user = models.OneToOneField(User, on_delete=models.CASCADE,
                              verbose_name='Пользователь')
  liked_recipes = models.ManyToManyField(Recipe, related_name='liked_by',
                                        blank=True, verbose_name='Лайкнутые рецепты')
  allergies = models.CharField(max_length=200, blank=True, verbose_name='Аллергии')
  # TODO: добавить `disliked_recipes` (ManyToManyField with Recipe) если будем использовать фичу дислайков

  def __str__(self):
    return self.user.username

  class Meta:
    verbose_name = 'Профиль пользователя'
    verbose_name_plural = 'Профили пользователей'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
  if created:
    UserProfile.objects.create(user=instance)