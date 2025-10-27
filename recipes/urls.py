from django.urls import path
from . import views


app_name = 'recipes'


urlpatterns = [
    path('', views.index, name='index'),
    path('recipe/', views.recipe_details, name='recipe_details'),
    path('recipe/<int:recipe_id>/', views.recipe_details, name='recipe_details_with_id'),
    path('recipe/reset/', views.recipe_details_reset, name='recipe_details_reset'),
    path('recipe/card/<int:recipe_id>/', views.recipe_card, name='recipe_card'),
    path('like/<int:recipe_id>/', views.like_recipe, name='like_recipe'),
    path('dislike/<int:recipe_id>/', views.dislike_recipe, name='dislike_recipe'),
    path('filters/', views.apply_filters, name='apply_filters'),
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('lk/', views.lk, name='lk'),
    path('refresh-breakfast/', views.refresh_breakfast, name='refresh_breakfast'),
    path('refresh-lunch/', views.refresh_lunch, name='refresh_lunch'),
    path('refresh-dinner/', views.refresh_dinner, name='refresh_dinner'),

]