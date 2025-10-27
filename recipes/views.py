from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from .models import Recipe, UserProfile, Ingredient
import random
import logging


logger = logging.getLogger(__name__)


def index(request):
    return render(request, 'index.html')


@login_required
def start_meal(request):
    if request.method == 'POST':
        for key in ['breakfast_recipe_id', 'lunch_recipe_id', 'dinner_recipe_id', 'recipe_filters']:
            request.session.pop(key, None)

        recipe = Recipe.objects.order_by('?').first()
        if recipe:
            request.session['dinner_recipe_id'] = recipe.id
        else:
            recipe = Recipe.objects.create(
                name="Тестовое блюдо",
                calories=300,
                meal_type='dinner',
                instructions="Добавьте рецепты в фикстуры."
            )
            request.session['dinner_recipe_id'] = recipe.id

        request.session['has_started'] = True

        return redirect('recipes:recipe_details')
    return redirect('recipes:index')


def recipe_details(request, recipe_id=None):
    if not request.user.is_authenticated:
        return redirect('recipes:login')

    try:
        profile = UserProfile.objects.get(user=request.user)
        profile.reset_refresh_counts()
        filters = profile.filters
    except UserProfile.DoesNotExist:
        filters = {}

    selected_meal_types = filters.get('meal_types', [])

    breakfast_id = request.session.get('breakfast_recipe_id')
    lunch_id = request.session.get('lunch_recipe_id')
    dinner_id = request.session.get('dinner_recipe_id')

    breakfast_recipe = lunch_recipe = dinner_recipe = None

    if 'breakfast' in selected_meal_types and breakfast_id:
        breakfast_recipe = _get_recipe_by_id(breakfast_id)
    if 'lunch' in selected_meal_types and lunch_id:
        lunch_recipe = _get_recipe_by_id(lunch_id)
    if 'dinner' in selected_meal_types and dinner_id:
        dinner_recipe = _get_recipe_by_id(dinner_id)

    if not selected_meal_types and dinner_id:
        dinner_recipe = _get_recipe_by_id(dinner_id)
        if not dinner_recipe:
            fallback = Recipe.objects.order_by('?').first()
            if fallback:
                request.session['dinner_recipe_id'] = fallback.id
                dinner_recipe = fallback

    if not (breakfast_recipe or lunch_recipe or dinner_recipe):
        fallback = Recipe.objects.order_by('?').first()
        if fallback:
            request.session['dinner_recipe_id'] = fallback.id
            dinner_recipe = fallback

    user_liked_ids = user_disliked_ids = []
    can_refresh = {'breakfast': True, 'lunch': True, 'dinner': True}
    remaining = {'breakfast': 3, 'lunch': 3, 'dinner': 3}

    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            user_liked_ids = list(profile.liked_recipes.values_list('id', flat=True))
            user_disliked_ids = list(profile.disliked_recipes.values_list('id', flat=True))

            can_refresh['breakfast'] = profile.can_refresh_breakfast()
            can_refresh['lunch'] = profile.can_refresh_lunch()
            can_refresh['dinner'] = profile.can_refresh_dinner()

            remaining['breakfast'] = 3 - profile.breakfast_refresh_count
            remaining['lunch'] = 3 - profile.lunch_refresh_count
            remaining['dinner'] = 3 - profile.dinner_refresh_count
        except UserProfile.DoesNotExist:
            pass

    has_started = request.session.get('has_started', False) or bool(dinner_id or breakfast_id or lunch_id)

    context = {
        'breakfast_recipe': breakfast_recipe,
        'lunch_recipe': lunch_recipe,
        'dinner_recipe': dinner_recipe,
        'show_breakfast': 'breakfast' in selected_meal_types,
        'show_lunch': 'lunch' in selected_meal_types,
        'show_dinner': 'dinner' in selected_meal_types or (not selected_meal_types),
        'dish_types': Recipe.TYPE_CHOICES,
        'filters': filters,
        'user_liked_ids': user_liked_ids,
        'user_disliked_ids': user_disliked_ids,
        'can_refresh_breakfast': can_refresh['breakfast'],
        'can_refresh_lunch': can_refresh['lunch'],
        'can_refresh_dinner': can_refresh['dinner'],
        'remaining_breakfast': remaining['breakfast'],
        'remaining_lunch': remaining['lunch'],
        'remaining_dinner': remaining['dinner'],
        'has_started': has_started,
    }

    return render(request, 'recipe-details.html', context)


def _get_recipe_by_id(recipe_id):
    try:
        return Recipe.objects.get(id=recipe_id)
    except Recipe.DoesNotExist:
        return None


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

    dinner_id = request.session.get('dinner_recipe_id')
    if not dinner_id:
        recipe = Recipe.objects.order_by('?').first()
        if recipe:
            request.session['dinner_recipe_id'] = recipe.id

    request.session['has_started'] = True

    return redirect('recipes:recipe_details')


def recipe_card(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    return render(request, 'recipe-card.html', {'recipe': recipe})


@login_required
def like_recipe(request, recipe_id):
    if request.method != 'POST':
        return redirect('recipes:recipe_details')
    recipe = get_object_or_404(Recipe, id=recipe_id)
    profile = UserProfile.objects.get(user=request.user)
    profile.disliked_recipes.remove(recipe)
    profile.liked_recipes.add(recipe)
    return redirect('recipes:recipe_details')


@login_required
def dislike_recipe(request, recipe_id):
    if request.method != 'POST':
        return redirect('recipes:recipe_details')
    recipe = get_object_or_404(Recipe, id=recipe_id)
    profile = UserProfile.objects.get(user=request.user)
    profile.liked_recipes.remove(recipe)
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

        for key in ['low_calorie', 'is_vegetarian', 'no_gluten']:
            if request.POST.get(key):
                filters[key] = True
        if request.POST.get('dish_type'):
            filters['dish_type'] = request.POST.get('dish_type')
        if request.POST.get('max_cost'):
            filters['max_cost'] = request.POST.get('max_cost')

        profile = UserProfile.objects.get(user=request.user)
        profile.filters = filters
        profile.save()
        request.session['recipe_filters'] = filters

        for meal in meal_types:
            if meal == 'breakfast' and profile.can_refresh_breakfast():
                recipes = get_filtered_recipes(filters, meal_type='breakfast', user=request.user)
                if recipes:
                    request.session['breakfast_recipe_id'] = random.choice(recipes).id
                    profile.apply_filters_breakfast()
            elif meal == 'lunch' and profile.can_refresh_lunch():
                recipes = get_filtered_recipes(filters, meal_type='lunch', user=request.user)
                if recipes:
                    request.session['lunch_recipe_id'] = random.choice(recipes).id
                    profile.apply_filters_lunch()
            elif meal == 'dinner' and profile.can_refresh_dinner():
                recipes = get_filtered_recipes(filters, meal_type='dinner', user=request.user)
                if recipes:
                    request.session['dinner_recipe_id'] = random.choice(recipes).id
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
            return render(request, 'registration.html', {'error': 'Email уже зарегистрирован'})
        user = User.objects.create_user(username=username, email=username, password=password, first_name=name)
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
def edit_profile(request):
    profile = UserProfile.objects.get(user=request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        allergies = request.POST.get('allergies', '').strip()

        request.user.first_name = name
        request.user.save()

        profile.allergies = allergies
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        profile.save()
        return redirect('recipes:lk')

    return render(request, 'edit-profile.html', {
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
        recipes = get_filtered_recipes(filters, meal_type='breakfast', user=request.user)
        if recipes:
            request.session['breakfast_recipe_id'] = random.choice(recipes).id
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
        recipes = get_filtered_recipes(filters, meal_type='lunch', user=request.user)
        if recipes:
            request.session['lunch_recipe_id'] = random.choice(recipes).id
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
        recipes = get_filtered_recipes(filters, meal_type='dinner', user=request.user)
        if recipes:
            request.session['dinner_recipe_id'] = random.choice(recipes).id
            profile.refresh_dinner()
        return redirect('recipes:recipe_details')
    return redirect('recipes:recipe_details')


def _update_session_recipes(request, disliked_recipe):
    filters = request.session.get('recipe_filters', {})
    mapping = [
        ('breakfast', 'breakfast_recipe_id'),
        ('lunch', 'lunch_recipe_id'),
        ('dinner', 'dinner_recipe_id')
    ]
    for meal, key in mapping:
        if request.session.get(key) == disliked_recipe.id:
            recipes = get_filtered_recipes(filters, meal_type=meal, user=request.user)
            if recipes:
                request.session[key] = random.choice(recipes).id
            else:
                request.session.pop(key, None)


def get_filtered_recipes(filters, meal_type=None, user=None):
    recipes = Recipe.objects.all()
    if meal_type:
        recipes = recipes.filter(meal_type=meal_type)

    if user and user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=user)
            if profile.allergies:
                user_allergies = [a.strip().lower() for a in profile.allergies.split(',') if a.strip()]
                if user_allergies:
                    q = Q()
                    for allergy in user_allergies:
                        q |= Q(allergens__icontains=allergy)
                    bad_ids = Ingredient.objects.filter(q).values_list('id', flat=True)
                    recipes = recipes.exclude(ingredients__id__in=bad_ids)
            recipes = recipes.exclude(id__in=profile.disliked_recipes.values_list('id', flat=True))
        except UserProfile.DoesNotExist:
            pass

    if filters.get('low_calorie'):
        recipes = recipes.filter(calories__lt=500)
    if filters.get('is_vegetarian'):
        recipes = recipes.filter(is_vegetarian=True)
    if filters.get('no_gluten'):
        recipes = recipes.filter(no_gluten=True)
    if filters.get('dish_type'):
        recipes = recipes.filter(dish_type=filters['dish_type'])

    filtered = list(recipes)
    if filters.get('max_cost'):
        try:
            max_cost = float(filters['max_cost'])
            filtered = [r for r in filtered if r.total_cost <= max_cost]
        except (ValueError, TypeError):
            pass

    if user and user.is_authenticated and filtered:
        try:
            profile = UserProfile.objects.get(user=user)
            liked_ids = set(profile.liked_recipes.values_list('id', flat=True))
            if liked_ids:
                weights = [3 if r.id in liked_ids else 1 for r in filtered]
                return [random.choices(filtered, weights=weights, k=1)[0]]
        except UserProfile.DoesNotExist:
            pass

    return filtered