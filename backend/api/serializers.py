import base64

from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import (Favorite, Follow, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCard, Tag, User)
from recipes.validation import validate_amount, validate_username


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = '__all__'


class Base64ImageField(serializers.ImageField):
    """Кастомное поле для работы с base64 изображениями."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя."""
    avatar = serializers.SerializerMethodField('get_image_url',
                                               read_only=True)
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')

    def get_image_url(self, obj):
        """Возвращает полный URL аватара пользователя."""
        if obj.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.avatar.url)
        return None

    def get_is_subscribed(self, obj):
        """Подписан ли текущий пользователь на этого пользователя."""
        user = self.context.get('request').user
        if user.is_authenticated:
            return Follow.objects.filter(user=obj, following=user).exists()
        return False


class AvatarSerializer(serializers.Serializer):
    """Сериализатор аватара."""
    avatar = Base64ImageField(required=True, allow_null=True,
                              write_only=True)

    def update(self, instance, validated_data):
        """Обновляет аватар пользователя."""
        avatar = validated_data.get('avatar')
        if avatar is not None:
            if instance.avatar:
                instance.avatar.delete(save=False)
            instance.avatar = avatar
            instance.save()
        return instance


class RecipeIngredientWriteSerializer(serializers.Serializer):
    """Сериализатор для записи ингредиента с количеством."""
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), required=True
    )
    amount = serializers.IntegerField(
        min_value=1,
        validators=[validate_amount], required=True
    )


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения ингредиентов с количеством."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""
    image = serializers.SerializerMethodField('get_image', read_only=True)
    tags = TagSerializer(read_only=True, many=True)
    author = UserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField(
        'is_favor', read_only=True
    )
    is_in_shopping_cart = serializers.SerializerMethodField(
        'is__in_shopping_cart', read_only=True
    )
    ingredients = RecipeIngredientReadSerializer(
        many=True,
        source='ingredient_amounts'
    )

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')

    def get_image(self, obj):
        """Возвращает полный URL изображения рецепта."""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def is_favor(self, obj):
        """Проверяет содержимое рецепта в избранном."""
        user = self.context.get('request').user
        if user.is_authenticated:
            return Favorite.objects.filter(author=user, recipe=obj).exists()
        return False

    def is__in_shopping_cart(self, obj):
        """Проверяет содержимое рецепта в корзине."""
        usr = self.context.get('request').user
        if usr.is_authenticated:
            return ShoppingCard.objects.filter(author=usr,
                                               recipe=obj).exists()
        return False


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для записи информации о рецептах."""
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), required=True
    )
    ingredients = RecipeIngredientWriteSerializer(many=True, required=True)
    image = Base64ImageField(required=True, write_only=True)

    class Meta:
        model = Recipe
        fields = ('ingredients', 'tags', 'image',
                  'name', 'text', 'cooking_time')

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                "Список тегов не может быть пустым."
            )
        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "Список ингредиентов не может быть пустым."
            )
        return value

    def validate(self, data):
        if 'tags' in data:
            tag_ids = [tag.id for tag in data['tags']]
            if len(tag_ids) != len(set(tag_ids)):
                raise serializers.ValidationError(
                    {'tags': ['Теги должны быть уникальными.']})

        if 'ingredients' in data:
            ingredient_ids = [item['id'].id for item in data['ingredients']]
            if len(ingredient_ids) != len(set(ingredient_ids)):
                raise serializers.ValidationError(
                    {'ingredients': ['Ингредиенты должны быть уникальными.']})

        return data

    def to_representation(self, value):
        """Преобразует объект для отображения."""
        return RecipeReadSerializer(value, context=self.context).data

    def create(self, validated_data):
        """Создает новый рецепт."""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        user = self.context['request'].user

        recipe = Recipe.objects.create(author=user, **validated_data)
        recipe.tags.set(tags_data)

        for ingredient_item in ingredients_data:
            ingredient = ingredient_item['id']
            amount = ingredient_item['amount']
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount
            )

        return recipe

    def update(self, instance, validated_data):
        """Обновляет существующий рецепт."""
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        if ingredients_data is None:
            raise serializers.ValidationError({
                'ingredients': 'Поле обязательно при обновлении рецепта.'
            })

        if tags_data is None:
            raise serializers.ValidationError({
                'tags': 'Поле обязательно при обновлении рецепта.'
            })

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.ingredient_amounts.all().delete()
            for ingredient_item in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient_item['id'],
                    amount=ingredient_item['amount']
                )

        return instance


class AdditionalSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для дополнительных моделей."""
    cooking_time = serializers.IntegerField(source='recipe.cooking_time')
    name = serializers.CharField(source='recipe.name')
    image = serializers.SerializerMethodField()

    class Meta:
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        """Возвращает полный URL изображения рецепта."""
        if obj.recipe.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.recipe.image.url)
        return None


class FavoriteSerializer(AdditionalSerializer):
    """Сериализатор для избранных рецептов."""
    class Meta(AdditionalSerializer.Meta):
        model = Favorite


class ShoppingListSerializer(AdditionalSerializer):
    """Сериализатор для списка покупок."""
    class Meta(AdditionalSerializer.Meta):
        model = ShoppingCard


class UserResponseSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения данных пользователя."""

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name')


class SignUpSerializer(serializers.Serializer):
    """Сериализатор для регистрации пользователей."""

    email = serializers.EmailField(
        required=True, max_length=254
    )
    username = serializers.CharField(
        required=True, max_length=150, validators=[validate_username]
    )
    first_name = serializers.CharField(
        required=True, max_length=150
    )
    last_name = serializers.CharField(
        required=True, max_length=150
    )
    password = serializers.CharField(
        required=True, max_length=128
    )

    def validate(self, data):
        email = data['email']
        username = data['username']
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                'email': 'Пользователь с таким email уже существует'
            })

        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError({
                'username': 'Пользователь с таким username уже существует'
            })

        return data

    def to_representation(self, instance):
        """Возвращаем данные через UserResponseSerializer после создания."""
        return UserResponseSerializer(instance).data

    def create(self, validated_data):
        """Создание пользователя."""
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password'],
            is_active=True
        )
        return user


class PasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        max_length=128, validators=[validate_password], write_only=True
    )
    current_password = serializers.CharField(
        max_length=128, validators=[validate_password], write_only=True
    )

    def validate_current_password(self, value):
        """Проверка, что текущий пароль указан верно."""
        user = self.context['request'].user

        if not user.check_password(value):
            raise serializers.ValidationError('Неверный текущий пароль')
        return value

    def validate(self, data):
        new_password = data['new_password']
        current_password = data['current_password']
        if new_password == current_password:
            raise serializers.ValidationError({
                'new_password': 'Новый пароль не может совпадать с текущим!',
            })
        return data

    def update(self, instance, validated_data):
        """Обновляет пароль пользователя."""
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Сериализатор для минифицированного отображения рецепта."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField('get_image_url',
                                               read_only=True)
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'avatar', 'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_image_url(self, obj):
        """Возвращает полный URL аватара пользователя."""
        if obj.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.avatar.url)
        return None

    def get_is_subscribed(self, obj):
        """Подписан ли текущий пользователь на этого пользователя."""
        user = self.context.get('request').user
        if user.is_authenticated:
            return Follow.objects.filter(user=obj, following=user).exists()
        return False

    def get_recipes(self, obj):
        """Возвращает рецепты пользователя с ограничением по recipes_limit."""
        recipes_limit = self.context.get('recipes_limit')
        recipes = obj.recipes.all()

        if recipes_limit:
            limit = int(recipes_limit)
            recipes = recipes[:limit]
        return RecipeMinifiedSerializer(
            recipes,
            many=True,
            context=self.context
        ).data
