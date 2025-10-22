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


def recipe_details(request, recipe_id=None):
  filters = request.session.get('recipe_filters', {})
  if recipe_id:
    recipe = get_object_or_404(Recipe, id=recipe_id)
  else:
    recipes = Recipe.objects.all()
    recipes = _apply_filters(recipes, filters)
    recipe = random.choice(list(recipes)) if recipes.exists() else None
  return render(request, 'recipe-details.html', {
    'recipe': recipe,
    'dish_types': Recipe.TYPE_CHOICES,
    'filters': filters,
  })


def recipe_details_reset(request):
  if 'recipe_filters' in request.session:
    del request.session['recipe_filters']
  return redirect('recipes:recipe_details')

def recipe_card(request, recipe_id):
  """Отображает карточку рецепта."""
  recipe = get_object_or_404(Recipe, id=recipe_id)
  return render(request, 'recipe-card.html', {'recipe': recipe})


@login_required
def like_recipe(request, recipe_id):
  if request.method != 'POST':
    return redirect('recipes:recipe_details')
  try:
    recipe = get_object_or_404(Recipe, id=recipe_id)
    profile = UserProfile.objects.get(user=request.user)
    if recipe not in profile.liked_recipes.all():
      profile.liked_recipes.add(recipe)
      logger.info(f"Recipe {recipe_id} liked")
    return redirect('recipes:recipe_details')
  except Exception as e:
    logger.error(f"Error liking recipe {recipe_id}: {str(e)}")
    return render(request, 'recipe-details.html', {
      'recipe': get_object_or_404(Recipe, id=recipe_id),
      'dish_types': Recipe.TYPE_CHOICES,
      'filters': request.session.get('recipe_filters', {}),
      'error': 'Ошибка при добавлении блюда в избранное'
    })


def dislike_recipe(request, recipe_id):
  if request.method != 'POST':
    return redirect('recipes:recipe_details')
  try:
    filters = request.session.get('recipe_filters', {})
    recipes = Recipe.objects.exclude(id=recipe_id)
    recipes = _apply_filters(recipes, filters)
    next_recipe = random.choice(list(recipes)) if recipes.exists() else None
    if next_recipe:
      return redirect('recipes:recipe_details_with_id',
                      recipe_id=next_recipe.id)
    return redirect('recipes:recipe_details')
  except Exception as e:
    logger.error(f"Error disliking recipe {recipe_id}: {str(e)}")
    return redirect('recipes:recipe_details')


@login_required
def apply_filters(request):
  if request.method != 'POST':
    return redirect('recipes:recipe_details')
  try:
    filters = {
      'low_calorie': request.POST.get('low_calorie') == 'on',
      'is_vegetarian': request.POST.get('is_vegetarian') == 'on',
      'dish_type': request.POST.get('dish_type') or '',
      'no_gluten': request.POST.get('no_gluten') == 'on',
      'max_cost': request.POST.get('max_cost', '')
    }
    request.session['recipe_filters'] = filters
    return redirect('recipes:recipe_details')
  except Exception as e:
    logger.error(f"Error applying filters: {str(e)}")
    return render(request, 'recipe-details.html', {
      'recipe': None,
      'dish_types': Recipe.TYPE_CHOICES,
      'filters': request.session.get('recipe_filters', {}),
      'error': 'Ошибка при применении фильтров'
    })


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