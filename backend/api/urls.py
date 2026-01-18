from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (IngredientViewSet, PasswordChangeViewSet, RecipeViewSet,
                       TagViewSet, UserViewSet)

router = DefaultRouter()

router.register('recipes', RecipeViewSet, basename='recipes')
router.register('users', UserViewSet, basename='users')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('tags', TagViewSet, basename='tags')


urlpatterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path(
        'users/set_password/',
        PasswordChangeViewSet.as_view({'post': 'set_password'}),
        name='set_password'
    ),
    path('', include(router.urls)),
]
