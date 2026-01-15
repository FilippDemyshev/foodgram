import re

from django.core.exceptions import ValidationError


def validate_time(value):
    if value < 1:
        raise ValidationError(
            'Время приготовления не может быть  меньше одной минуты'
        )
    if value > 360:
        raise ValidationError(
            'Время приготовления не может быть больще 6 часов'
        )


def validate_name(value):
    if not re.match(r'^[-a-zA-Z0-9_]+$', value):
        raise ValidationError(
            'Slug может содержать только латинские буквы, цифры, '
            'дефисы и нижние подчеркивания.'
        )


def validate_amount(value):
    if value < 1:
        raise ValidationError(
            'Количесвто указанного ингридиента не может быть меньше 1'
        )


def validate_username(value):
    """Валидатор для проверки, что username не 'me'."""
    if value.lower() == 'me':
        raise ValidationError('Имя пользователя "me" запрещено')

    pattern = r'^[\w.@+-]+\Z'
    if not re.match(pattern, value):
        raise ValidationError(
            'Имя пользователя содержит недопустимые символы. '
            'Допустимы только буквы, цифры и символы @/./+/-/_'
        )

    return value
