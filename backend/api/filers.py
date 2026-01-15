from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe, Tag


class RecipeFilter(filters.FilterSet):
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_shopping_cart')
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    author = filters.NumberFilter(field_name='author__id')

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']

    def filter_is_favorited(self, queryset, name, value):
        """
        Фильтрация по избранному.
        Только value=1 фильтрует, value=0 игнорируется.
        """
        user = self.request.user

        if int(value) == 1:
            if not user.is_authenticated:
                return queryset.none()
            return queryset.filter(favorites__author=user)
        return queryset

    def filter_is_shopping_cart(self, queryset, name, value):
        """
        Фильтрация по списку покупок.
        Только value=1 фильтрует, value=0 игнорируется.
        """
        user = self.request.user

        if int(value) == 1:
            if not user.is_authenticated:
                return queryset.none()
            return queryset.filter(shopping__author=user)

        return queryset


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(
        lookup_expr='istartswith',
        field_name='name'
    )

    class Meta:
        model = Ingredient
        fields = ['name']
