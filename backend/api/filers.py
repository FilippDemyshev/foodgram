from django_filters import rest_framework as filters
from rest_framework import filters as fl

from recipes.models import Recipe, Tag


class RecipeFilter(filters.FilterSet):
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_shopping_cart'
    )
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']

    def filter_is_favorited(self, queryset, name, value):
        """
        Фильтрация по избранному.
        Только value=True фильтрует, value=False игнорируется.
        """
        user = self.request.user

        if value:
            if not user.is_authenticated:
                return queryset.none()
            return queryset.filter(favorites__author=user)
        return queryset

    def filter_is_shopping_cart(self, queryset, name, value):
        """
        Фильтрация по списку покупок.
        Только value=True фильтрует, value=False игнорируется.
        """
        user = self.request.user

        if value:
            if not user.is_authenticated:
                return queryset.none()
            return queryset.filter(shopping__author=user)

        return queryset


class IngredientSearchFilter(fl.SearchFilter):
    """
    Кастомный SearchFilter для ингредиентов.
    Использует параметр ?name= вместо стандартного ?search=
    """

    search_param = 'name'
