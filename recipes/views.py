from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from .models import Recipe, UserProfile
import random
import logging


logger = logging.getLogger(__name__)


def _apply_filters(recipes, filters):
  if filters.get('low_calorie', False):
    recipes = recipes.filter(calories__lt=500)
  if filters.get('is_vegetarian', False):
    recipes = recipes.filter(is_vegetarian=True)
  if filters.get('dish_type'):
    recipes = recipes.filter(dish_type=filters['dish_type'])
  if filters.get('no_gluten', False):
    recipes = recipes.filter(no_gluten=True)
  if filters.get('max_cost'):
    try:
      max_cost = float(filters['max_cost'])
      recipes = recipes.filter(id__in=[r.id for r in recipes
                                      if r.total_cost() <= max_cost])
    except (ValueError, TypeError):
      logger.warning("Invalid max_cost value in filters")
  return recipes


def index(request):
  return render(request, 'index.html')

@login_required
def recipe_details(request, recipe_id=None):
  if request.user.is_authenticated:
    try:
      profile = UserProfile.objects.get(user=request.user)
      filters = profile.filters
      profile.reset_refresh_counts()
    except UserProfile.DoesNotExist:
      filters = {}
  else:
    filters = request.session.get('recipe_filters', {})

  selected_meal_types = filters.get('meal_types', [])

  breakfast_recipe = None
  lunch_recipe = None
  dinner_recipe = None

  show_all = not selected_meal_types

  user_liked_ids = []
  user_disliked_ids = []
  can_refresh_breakfast = True
  can_refresh_lunch = True
  can_refresh_dinner = True
  remaining_breakfast = 3
  remaining_lunch = 3
  remaining_dinner = 3

  if request.user.is_authenticated:
    try:
      profile = UserProfile.objects.get(user=request.user)
      user_liked_ids = list(profile.liked_recipes.values_list('id', flat=True))
      user_disliked_ids = list(profile.disliked_recipes.values_list('id', flat=True))
      can_refresh_breakfast = profile.can_refresh_breakfast()
      can_refresh_lunch = profile.can_refresh_lunch()
      can_refresh_dinner = profile.can_refresh_dinner()
      remaining_breakfast = 3 - profile.breakfast_refresh_count
      remaining_lunch = 3 - profile.lunch_refresh_count
      remaining_dinner = 3 - profile.dinner_refresh_count
    except UserProfile.DoesNotExist:
      pass


  if show_all or 'breakfast' in selected_meal_types:
    breakfast_id = request.session.get('breakfast_recipe_id')
    if breakfast_id:
      try:
        breakfast_recipe = Recipe.objects.get(id=breakfast_id)
      except Recipe.DoesNotExist:
        pass

  if show_all or 'lunch' in selected_meal_types:
    lunch_id = request.session.get('lunch_recipe_id')
    if lunch_id:
      try:
        lunch_recipe = Recipe.objects.get(id=lunch_id)
      except Recipe.DoesNotExist:
        pass

  if show_all or 'dinner' in selected_meal_types:
    dinner_id = request.session.get('dinner_recipe_id')
    if dinner_id:
      try:
        dinner_recipe = Recipe.objects.get(id=dinner_id)
      except Recipe.DoesNotExist:
        pass

  recipe = lunch_recipe or breakfast_recipe or dinner_recipe

  return render(request, 'recipe-details.html', {
    'recipe': recipe,
    'breakfast_recipe': breakfast_recipe,
    'lunch_recipe': lunch_recipe,
    'dinner_recipe': dinner_recipe,
    'show_breakfast': show_all or 'breakfast' in selected_meal_types,
    'show_lunch': show_all or 'lunch' in selected_meal_types,
    'show_dinner': show_all or 'dinner' in selected_meal_types,
    'dish_types': Recipe.TYPE_CHOICES,
    'filters': filters,
    'user_liked_ids': user_liked_ids,
    'user_disliked_ids': user_disliked_ids,
    'can_refresh_breakfast': can_refresh_breakfast,
    'can_refresh_lunch': can_refresh_lunch,
    'can_refresh_dinner': can_refresh_dinner,
    'remaining_breakfast': remaining_breakfast,
    'remaining_lunch': remaining_lunch,
    'remaining_dinner': remaining_dinner,
  })


@login_required
def recipe_details_reset(request):
  try:
    profile = UserProfile.objects.get(user=request.user)
    profile.filters = {}
    profile.save()
  except UserProfile.DoesNotExist:
    pass

  request.session.pop('recipe_filters', None)
  request.session.pop('breakfast_recipe_id', None)
  request.session.pop('lunch_recipe_id', None)
  request.session.pop('dinner_recipe_id', None)

  return redirect('recipes:recipe_details')

def recipe_card(request, recipe_id):
  """Отображает карточку рецепта."""
  recipe = get_object_or_404(Recipe, id=recipe_id)
  return render(request, 'recipe-card.html', {'recipe': recipe})


@login_required
def like_recipe(request, recipe_id):
  if request.method != 'POST':
    return redirect('recipes:recipe_details')

  recipe = get_object_or_404(Recipe, id=recipe_id)
  profile = UserProfile.objects.get(user=request.user)

  if recipe in profile.disliked_recipes.all():
    profile.disliked_recipes.remove(recipe)

  if recipe not in profile.liked_recipes.all():
    profile.liked_recipes.add(recipe)

  return redirect('recipes:recipe_details')

@login_required
def dislike_recipe(request, recipe_id):
  if request.method != 'POST':
    return redirect('recipes:recipe_details')

  recipe = get_object_or_404(Recipe, id=recipe_id)
  profile = UserProfile.objects.get(user=request.user)

  if recipe in profile.liked_recipes.all():
    profile.liked_recipes.remove(recipe)

  if recipe not in profile.disliked_recipes.all():
    profile.disliked_recipes.add(recipe)

  _update_session_recipes(request, recipe)

  return redirect('recipes:recipe_details')



@login_required
def apply_filters(request):
    if request.method == 'POST':
        filters = {}

        meal_types = request.POST.getlist('meal_types')
        if meal_types:
            filters['meal_types'] = meal_types

        if request.POST.get('low_calorie'):
            filters['low_calorie'] = True

        if request.POST.get('is_vegetarian'):
            filters['is_vegetarian'] = True

        if request.POST.get('no_gluten'):
            filters['no_gluten'] = True

        dish_type = request.POST.get('dish_type')
        if dish_type:
            filters['dish_type'] = dish_type

        max_cost = request.POST.get('max_cost')
        if max_cost:
            filters['max_cost'] = max_cost

        profile = UserProfile.objects.get(user=request.user)
        profile.filters = filters
        profile.save()

        request.session['recipe_filters'] = filters


        if 'breakfast' in meal_types or not meal_types:
            if profile.can_refresh_breakfast():
                breakfast_recipes = get_filtered_recipes(filters, meal_type='breakfast', user=request.user)
                if breakfast_recipes:
                    new_recipe = random.choice(breakfast_recipes)
                    request.session['breakfast_recipe_id'] = new_recipe.id
                    profile.apply_filters_breakfast()


        if 'lunch' in meal_types or not meal_types:
            if profile.can_refresh_lunch():
                lunch_recipes = get_filtered_recipes(filters, meal_type='lunch', user=request.user)
                if lunch_recipes:
                    new_recipe = random.choice(lunch_recipes)
                    request.session['lunch_recipe_id'] = new_recipe.id
                    profile.apply_filters_lunch()


        if 'dinner' in meal_types or not meal_types:
            if profile.can_refresh_dinner():
                dinner_recipes = get_filtered_recipes(filters, meal_type='dinner', user=request.user)
                if dinner_recipes:
                    new_recipe = random.choice(dinner_recipes)
                    request.session['dinner_recipe_id'] = new_recipe.id
                    profile.apply_filters_dinner()

        return redirect('recipes:recipe_details')

    return redirect('recipes:recipe_details')

def user_login(request):
  if request.method == 'POST':
    username = request.POST['email']
    password = request.POST['password']
    user = authenticate(request, username=username, password=password)
    if user:
      login(request, user)
      next_url = request.GET.get('next', 'recipes:lk')
      return redirect(next_url)
    return render(request, 'auth.html', {
      'error': 'Неверный email или пароль',
      'next': request.GET.get('next', '')
    })
  next_url = request.GET.get('next', '')
  return render(request, 'auth.html', {'next': next_url})


def register(request):
  if request.method == 'POST':
    username = request.POST['email']
    password = request.POST['password']
    name = request.POST['name']
    if User.objects.filter(username=username).exists():
      return render(request, 'registration.html',
                    {'error': 'Email уже зарегистрирован'})
    user = User.objects.create_user(username=username, email=username,
                                    password=password, first_name=name)
    login(request, user)
    next_url = request.GET.get('next', 'recipes:lk')
    return redirect(next_url)
  return render(request, 'registration.html')


@login_required
def user_logout(request):
  logout(request)
  return redirect('recipes:index')


@login_required
def lk(request):
  profile = UserProfile.objects.get(user=request.user)
  liked_recipes = profile.liked_recipes.all()
  return render(request, 'lk.html', {
    'liked_recipes': liked_recipes,
    'user': request.user,
    'profile': profile
  })


@login_required
def refresh_breakfast(request):
  if request.method == 'POST':
    profile = UserProfile.objects.get(user=request.user)

    if not profile.can_refresh_breakfast():
      return redirect('recipes:recipe_details')

    filters = request.session.get('recipe_filters', {})
    breakfast_recipes = get_filtered_recipes(filters, meal_type='breakfast', user=request.user)

    if breakfast_recipes:
      new_recipe = random.choice(breakfast_recipes)
      request.session['breakfast_recipe_id'] = new_recipe.id
      profile.refresh_breakfast()

    return redirect('recipes:recipe_details')
  return redirect('recipes:recipe_details')


@login_required
def refresh_lunch(request):
  if request.method == 'POST':
    profile = UserProfile.objects.get(user=request.user)

    if not profile.can_refresh_lunch():
      return redirect('recipes:recipe_details')

    filters = request.session.get('recipe_filters', {})
    lunch_recipes = get_filtered_recipes(filters, meal_type='lunch', user=request.user)

    if lunch_recipes:
      new_recipe = random.choice(lunch_recipes)
      request.session['lunch_recipe_id'] = new_recipe.id
      profile.refresh_lunch()

    return redirect('recipes:recipe_details')
  return redirect('recipes:recipe_details')


@login_required
def refresh_dinner(request):
  if request.method == 'POST':
    profile = UserProfile.objects.get(user=request.user)

    if not profile.can_refresh_dinner():
      return redirect('recipes:recipe_details')

    filters = request.session.get('recipe_filters', {})
    dinner_recipes = get_filtered_recipes(filters, meal_type='dinner', user=request.user)

    if dinner_recipes:
      new_recipe = random.choice(dinner_recipes)
      request.session['dinner_recipe_id'] = new_recipe.id
      profile.refresh_dinner()

    return redirect('recipes:recipe_details')
  return redirect('recipes:recipe_details')




def _update_session_recipes(request, disliked_recipe):
    filters = request.session.get('recipe_filters', {})

    breakfast_id = request.session.get('breakfast_recipe_id')
    if breakfast_id == disliked_recipe.id:
      breakfast_recipes = get_filtered_recipes(filters, meal_type='breakfast', user=request.user)
      if breakfast_recipes:
        request.session['breakfast_recipe_id'] = random.choice(breakfast_recipes).id
      else:
        request.session.pop('breakfast_recipe_id', None)

    lunch_id = request.session.get('lunch_recipe_id')
    if lunch_id == disliked_recipe.id:
      lunch_recipes = get_filtered_recipes(filters, meal_type='lunch', user=request.user)
      if lunch_recipes:
        request.session['lunch_recipe_id'] = random.choice(lunch_recipes).id
      else:
        request.session.pop('lunch_recipe_id', None)

    dinner_id = request.session.get('dinner_recipe_id')
    if dinner_id == disliked_recipe.id:
      dinner_recipes = get_filtered_recipes(filters, meal_type='dinner', user=request.user)
      if dinner_recipes:
        request.session['dinner_recipe_id'] = random.choice(dinner_recipes).id
      else:
        request.session.pop('dinner_recipe_id', None)


def get_filtered_recipes(filters, meal_type=None, user=None):
  recipes = Recipe.objects.all()

  if user and user.is_authenticated:
    try:
      profile = UserProfile.objects.get(user=user)
      disliked_recipe_ids = profile.disliked_recipes.values_list('id', flat=True)
      recipes = recipes.exclude(id__in=disliked_recipe_ids)
    except UserProfile.DoesNotExist:
      pass

  if meal_type:
    recipes = recipes.filter(meal_type=meal_type)

  if filters.get('low_calorie'):
    recipes = recipes.filter(calories__lt=500)
  if filters.get('is_vegetarian'):
    recipes = recipes.filter(is_vegetarian=True)
  if filters.get('no_gluten'):
    recipes = recipes.filter(no_gluten=True)
  if filters.get('dish_type'):
    recipes = recipes.filter(dish_type=filters['dish_type'])

  filtered_recipes = list(recipes)

  if filters.get('max_cost'):
    try:
      max_cost = float(filters['max_cost'])
      filtered_recipes = [r for r in filtered_recipes if r.total_cost <= max_cost]
    except (ValueError, TypeError):
      pass

  # Сделал приоритет по весу
  if user and user.is_authenticated and filtered_recipes:
    try:
      profile = UserProfile.objects.get(user=user)
      liked_recipe_ids = set(profile.liked_recipes.values_list('id', flat=True))

      if liked_recipe_ids:
        weights = []
        for recipe in filtered_recipes:
          if recipe.id in liked_recipe_ids:
            weights.append(3)
          else:
            weights.append(1)

        chosen_recipe = random.choices(filtered_recipes, weights=weights, k=1)[0]
        return [chosen_recipe]

    except UserProfile.DoesNotExist:
      pass

  return filtered_recipes