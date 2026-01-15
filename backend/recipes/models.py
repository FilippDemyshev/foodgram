from django.contrib.auth.models import AbstractUser
from django.db import models

from .validation import (validate_amount, validate_name, validate_time,
                         validate_username)


class User(AbstractUser):
    """Модель пользователя."""

    username = models.CharField(
        "Имя пользователя",
        max_length=150,
        unique=True,
        validators=[validate_username]
    )
    first_name = models.CharField('Имя', max_length=150, blank=False)
    last_name = models.CharField('Фамилия', max_length=150, blank=False)
    email = models.EmailField("Электронная почта", max_length=254,
                              unique=True)
    password = models.CharField("Пароль", max_length=128, blank=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        """Метаданные модели пользователя."""
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        """Строковое представление пользователя."""
        return self.username


class Tag(models.Model):
    """Модель тега."""
    name = models.CharField(max_length=32, verbose_name='Название')
    slug = models.CharField(max_length=32, unique=True,
                            validators=[validate_name], verbose_name='Слаг')

    class Meta:
        """Метаданные модели тега."""
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        """Строковое представление тега."""
        return f"{self.name}"


class Ingredient(models.Model):
    """Модель ингредиента."""
    name = models.CharField(max_length=128,
                            verbose_name='Название ингредиента')
    measurement_unit = models.CharField(max_length=64,
                                        verbose_name='Единица измерения')

    class Meta:
        """Метаданные модели ингредиента."""
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        """Строковое представление ингредиента."""
        return f"{self.name}, {self.measurement_unit}"


class Recipe(models.Model):
    """Модель рецепта."""
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='recipes'
    )
    name = models.CharField(max_length=256, verbose_name='Блюдо')
    image = models.ImageField(upload_to='recipes/images/',
                              verbose_name='Картинка')
    text = models.TextField(verbose_name='Описание')
    tags = models.ManyToManyField(Tag, verbose_name='Тег',
                                  related_name='recipes')
    cooking_time = models.PositiveSmallIntegerField(
        validators=[validate_time],
        verbose_name='Время приготовления'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты',
        related_name='recipes'
    )

    class Meta:
        """Метаданные модели рецепта."""
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        """Строковое представление рецепта."""
        return f"{self.name} (автор: {self.author.username})"


class RecipeIngredient(models.Model):
    """Промежуточная модель для связи Рецепт-Ингредиент с количеством."""
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_amounts',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe_amounts',
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        validators=[validate_amount],
        verbose_name='Количество'
    )

    class Meta:
        """Метаданные модели ингредиента рецепта."""
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'

    def __str__(self):
        """Строковое представление ингредиента рецепта."""
        return (f"{self.recipe.name} {self.ingredient.name} - {self.amount} "
                f"{self.ingredient.measurement_unit}")


class Favorite(models.Model):
    """Модель избранного."""
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='favorites'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='favorites'
    )

    class Meta:
        """Метаданные модели избранного."""
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        """Строковое представление избранного."""
        return (f'{self.author.username} добавил(а) "{self.recipe.name}" '
                f'в избранное')


class ShoppingCard(models.Model):
    """Модель корзины покупок."""
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='shopping'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='shopping'
    )

    class Meta:
        """Метаданные модели корзины."""
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзина'

    def __str__(self):
        """Строковое представление корзины."""
        return (f'🛒 {self.author.username} добавил(а) "{self.recipe.name}" '
                f'в список покупок')


class Follow(models.Model):
    """Модель для подписок пользователей друг на друга."""

    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='follower')
    following = models.ForeignKey(User, on_delete=models.CASCADE,
                                  related_name='following')

    class Meta:
        """Мета-класс для настройки модели Follow."""
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'following'],
                name='unique_follow',
                violation_error_message='Вы уже подписаны на этого юзера'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('following')),
                name='prevent_self_follow',
                violation_error_message='Нельзя подписаться на самого себя'
            )
        ]

    def __str__(self):
        """Строковое представление подписки."""
        return f'{self.user.username} подписан на {self.following.username}'
