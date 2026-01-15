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


class RecipeAdmin(admin.ModelAdmin):
    """Админ-панель для модели рецепта."""
    list_display = (
        'author',
        'name',
        'text',
        'display_tags',
        'cooking_time',
        'favorite_count'
    )
    search_fields = (
        'name',
        'author__username',
    )
    list_filter = ('tags',)

    def display_tags(self, obj):
        """Отображение тегов рецепта."""
        return ", ".join([tag.name for tag in obj.tags.all()])

    display_tags.short_description = 'Теги'

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
admin.site.register(RecipeIngredient)
