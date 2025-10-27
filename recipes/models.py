from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


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

  MEAL_TYPE_CHOICES = [
    ('breakfast', 'Завтрак'),
    ('lunch', 'Обед'),
    ('dinner', 'Ужин'),
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

  meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES,
                               default='lunch', verbose_name='Тип приема пищи')

  @property
  def total_cost(self):
    return sum(ingredient.cost for ingredient in self.ingredients.all())

  def __str__(self):
    return self.name

  class Meta:
    verbose_name = 'Рецепт'
    verbose_name_plural = 'Рецепты'


class UserProfile(models.Model):
  user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')
  liked_recipes = models.ManyToManyField(Recipe, related_name='liked_by', blank=True, verbose_name='Лайкнутые рецепты')
  disliked_recipes = models.ManyToManyField(Recipe, related_name='disliked_by', blank=True,
                                            verbose_name='Дизлайкнутые рецепты')
  allergies = models.CharField(max_length=200, blank=True, verbose_name='Аллергии')
  filters = models.JSONField(default=dict, blank=True, verbose_name='Фильтры пользователя')

  breakfast_refresh_count = models.IntegerField(default=0, verbose_name='Счетчик обновлений завтрака')
  lunch_refresh_count = models.IntegerField(default=0, verbose_name='Счетчик обновлений обеда')
  dinner_refresh_count = models.IntegerField(default=0, verbose_name='Счетчик обновлений ужина')
  last_refresh_date = models.DateTimeField(default=timezone.now, verbose_name='Дата последнего обновления')

  breakfast_blocked_until = models.DateTimeField(null=True, blank=True, verbose_name='Блокировка завтрака до')
  lunch_blocked_until = models.DateTimeField(null=True, blank=True, verbose_name='Блокировка обеда до')
  dinner_blocked_until = models.DateTimeField(null=True, blank=True, verbose_name='Блокировка ужина до')

  def __str__(self):
    return self.user.username

  def reset_refresh_counts(self):
    now = timezone.now()
    if now - self.last_refresh_date > timedelta(hours=24):
      self.breakfast_refresh_count = 0
      self.lunch_refresh_count = 0
      self.dinner_refresh_count = 0
      self.last_refresh_date = now
      self.breakfast_blocked_until = None
      self.lunch_blocked_until = None
      self.dinner_blocked_until = None
      self.save()

  def can_refresh_breakfast(self):
    self.reset_refresh_counts()
    if self.breakfast_blocked_until and timezone.now() < self.breakfast_blocked_until:
      return False
    return self.breakfast_refresh_count < 3

  def can_refresh_lunch(self):
    self.reset_refresh_counts()
    if self.lunch_blocked_until and timezone.now() < self.lunch_blocked_until:
      return False
    return self.lunch_refresh_count < 3

  def can_refresh_dinner(self):
    self.reset_refresh_counts()
    if self.dinner_blocked_until and timezone.now() < self.dinner_blocked_until:
      return False
    return self.dinner_refresh_count < 3

  def refresh_breakfast(self):
    self.reset_refresh_counts()
    self.breakfast_refresh_count += 1
    self.last_refresh_date = timezone.now()

    if self.breakfast_refresh_count >= 3:
      self.breakfast_blocked_until = timezone.now() + timedelta(hours=24)

    self.save()

  def refresh_lunch(self):
    self.reset_refresh_counts()
    self.lunch_refresh_count += 1
    self.last_refresh_date = timezone.now()

    if self.lunch_refresh_count >= 3:
      self.lunch_blocked_until = timezone.now() + timedelta(hours=24)

    self.save()

  def refresh_dinner(self):
    self.reset_refresh_counts()
    self.dinner_refresh_count += 1
    self.last_refresh_date = timezone.now()

    if self.dinner_refresh_count >= 3:
      self.dinner_blocked_until = timezone.now() + timedelta(hours=24)

    self.save()

  def apply_filters_breakfast(self):
    self.reset_refresh_counts()
    if self.breakfast_refresh_count < 3:
      self.breakfast_refresh_count += 1
      self.last_refresh_date = timezone.now()

      if self.breakfast_refresh_count >= 3:
        self.breakfast_blocked_until = timezone.now() + timedelta(hours=24)

      self.save()
      return True
    return False

  def apply_filters_lunch(self):
    self.reset_refresh_counts()
    if self.lunch_refresh_count < 3:
      self.lunch_refresh_count += 1
      self.last_refresh_date = timezone.now()

      if self.lunch_refresh_count >= 3:
        self.lunch_blocked_until = timezone.now() + timedelta(hours=24)

      self.save()
      return True
    return False

  def apply_filters_dinner(self):
    self.reset_refresh_counts()
    if self.dinner_refresh_count < 3:
      self.dinner_refresh_count += 1
      self.last_refresh_date = timezone.now()

      if self.dinner_refresh_count >= 3:
        self.dinner_blocked_until = timezone.now() + timedelta(hours=24)

      self.save()
      return True
    return False

  class Meta:
    verbose_name = 'Профиль пользователя'
    verbose_name_plural = 'Профили пользователей'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
  if created:
    UserProfile.objects.create(user=instance)