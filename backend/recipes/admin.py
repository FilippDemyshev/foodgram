from django.contrib import admin

from .models import (Favorite, Follow, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCard, Tag, User)


class UserAdmin(admin.ModelAdmin):
    """Админ-панель для модели пользователя."""
    list_display = (
        'username',
        'first_name',
        'last_name',
        'email',
    )
    search_fields = (
        'username',
        'email'
    )


class RecipeIngredientInline(admin.TabularInline):
    """Inline-форма для управления ингредиентами рецепта с количеством."""
    model = RecipeIngredient
    extra = 3
    min_num = 1
    validate_min = True
    autocomplete_fields = ['ingredient']


class RecipeAdmin(admin.ModelAdmin):
    """Админ-панель для модели рецепта."""
    list_display = (
        'author',
        'name',
        'text',
        'display_tags',
        'get_ingredients',
        'cooking_time',
        'favorite_count'
    )
    search_fields = (
        'name',
        'author__username',
    )
    list_filter = ('tags',)

    inlines = [RecipeIngredientInline]

    def display_tags(self, obj):
        """Отображение тегов рецепта."""
        return ", ".join([tag.name for tag in obj.tags.all()])

    display_tags.short_description = 'Теги'

    def get_ingredients(self, obj):
        return ", ".join([
            f"{ing.name}" for ing in obj.ingredients.all()[:3]
        ])
    get_ingredients.short_description = 'Ингредиенты'

    def favorite_count(self, obj):
        """Количество добавлений рецепта в избранное."""
        return obj.favorites.count()

    favorite_count.short_description = 'Добавлений в избранное'


class IngredientAdmin(admin.ModelAdmin):
    """Админ-панель для модели ингредиента."""
    list_display = (
        'name',
        'measurement_unit',
    )
    search_fields = ('name',)


admin.site.register(Tag)
admin.site.register(User, UserAdmin)
admin.site.register(Follow)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Favorite)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(ShoppingCard)
