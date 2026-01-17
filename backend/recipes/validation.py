import re

from django.core.exceptions import ValidationError

from .constants import MAX_COOKING_TIME, MIN_AMOUNT, MIN_COOKING_TIME


def validate_time(value):
    if value < MIN_COOKING_TIME:
        raise ValidationError(
            'Время приготовления не может быть '
            f'меньше {MIN_COOKING_TIME} минуты'
        )
    if value > MAX_COOKING_TIME:
        raise ValidationError(
            'Время приготовления не может быть '
            f'больше {MAX_COOKING_TIME} минут'
        )


def validate_name(value):
    if not re.match(r'^[-a-zA-Z0-9_]+$', value):
        raise ValidationError(
            'Slug может содержать только латинские буквы, цифры, '
            'дефисы и нижние подчеркивания.'
        )


def validate_amount(value):
    if value < MIN_AMOUNT:
        raise ValidationError(
            f'Указанного ингредиента не может быть меньше {MIN_AMOUNT}'
        )


def validate_username(value):
    """Валидатор для проверки, что username не 'me'."""
    pattern = r'^[\w.@+-]+\Z'
    if not re.match(pattern, value):
        raise ValidationError(
            'Имя пользователя содержит недопустимые символы. '
            'Допустимы только буквы, цифры и символы @/./+/-/_'
        )

    return value
