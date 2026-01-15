from datetime import datetime

from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.models import (Favorite, Follow, Ingredient, Recipe, ShoppingCard,
                            Tag, User)
from .filers import IngredientFilter, RecipeFilter
from .permissions import IsAuthorOrReadOnlyPermission
from .serializers import (AvatarSerializer, FavoriteSerializer,
                          FollowSerializer, IngredientSerializer,
                          PasswordSerializer, RecipeReadSerializer,
                          RecipeWriteSerializer, ShoppingListSerializer,
                          SignUpSerializer, TagSerializer, UserSerializer)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для работы с тегами."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для работы с ингредиентами."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с пользователями."""
    queryset = User.objects.all()
    # serializer_class = UserSerializer
    permission_classes = [AllowAny]
    http_method_names = ['get', 'post', 'delete', 'put']
    pagination_class = LimitOffsetPagination

    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор для действия."""
        if self.action in ("create", ):
            return SignUpSerializer
        elif self.action == "my_avatar":
            return AvatarSerializer
        elif self.action == 'set_password':
            return PasswordSerializer
        elif self.action in ("list", "retrieve"):
            return UserSerializer
        elif self.action == "subscribe":
            return FollowSerializer
        elif self.action == "subscriptions":
            return FollowSerializer
        return UserSerializer

    @action(
        methods=["get"],
        detail=False,
        url_path="me",
        serializer_class=UserSerializer,
        permission_classes=[IsAuthenticated]
    )
    def users_own_profile(self, request):
        """Возвращает профиль текущего пользователя."""
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["put", "delete"],
        detail=False,
        url_path="me/avatar",
        serializer_class=AvatarSerializer,
        permission_classes=[IsAuthenticated]
    )
    def my_avatar(self, request):
        """Управляет аватаром текущего пользователя."""
        user = request.user
        if request.method == "PUT":
            serializer = self.get_serializer(user, data=request.data)
            if not serializer.is_valid():
                return Response(
                    serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )

            user = serializer.save()
            avatar_url = (
                request.build_absolute_uri(user.avatar.url)
                if user.avatar else None
            )
            return Response(
                {"avatar": avatar_url}, status=status.HTTP_200_OK
            )

        elif request.method == "DELETE":
            if user.avatar:
                user.avatar.delete()
                user.avatar = None
                user.save()
                return Response(
                    {"detail": "Аватар успешно удален"},
                    status=status.HTTP_204_NO_CONTENT
                )
            return Response(
                {"detail": "Аватар не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(
        methods=["post"],
        detail=False,
        url_path="set_password",
        serializer_class=PasswordSerializer,
        permission_classes=[IsAuthenticated]
    )
    def set_password(self, request):
        """Смена пароля."""
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=["post", "delete"],
        detail=True,
        url_path="subscribe",
        serializer_class=FollowSerializer,
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk):
        user = request.user
        recipes_limit = request.query_params.get('recipes_limit')
        following = get_object_or_404(User, pk=pk)
        follow = Follow.objects.filter(user=user, following=following)
        if request.method == 'POST':
            if follow.exists():
                return Response(
                    {"detail": "Вы уже подписаны на этого человека!"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if user == following:
                return Response({"detail": "Нельзя подписаться на себя!"},
                                status=status.HTTP_400_BAD_REQUEST)

            Follow.objects.create(user=user, following=following)

            serializer = FollowSerializer(
                following,
                context={'request': request, 'recipes_limit': recipes_limit}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if not follow.exists():
                return Response(
                    {"detail": "Вы не подписаны на этого человека!"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=["get"],
        detail=False,
        url_path="subscriptions",
        serializer_class=FollowSerializer,
        permission_classes=[IsAuthenticated],
        pagination_class=LimitOffsetPagination
    )
    def subscriptions(self, request):
        user = request.user
        recipes_limit = request.query_params.get('recipes_limit')
        following_users = User.objects.filter(
            following__user=user).prefetch_related('recipes')
        paginated_queryset = self.paginate_queryset(following_users)
        serializer = FollowSerializer(
            paginated_queryset, context={
                'request': request, 'recipes_limit': recipes_limit}, many=True)
        return self.get_paginated_response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Удаление пользователей запрещено"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для управления рецептами."""
    queryset = Recipe.objects.all()
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = 'pk'
    permission_classes = (IsAuthorOrReadOnlyPermission, )
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор для действия."""
        if self.action in ("list", "retrieve"):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(methods=["get"], detail=True, url_path="get-link")
    def get_recipe_url(self, request, pk):
        """Возвращает абсолютный URL рецепта."""
        recipe = self.get_object()
        return Response({'short-link': request.build_absolute_uri(recipe)})

    @action(methods=["post", "delete"], detail=True, url_path="favorite",
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        """Добавляет или удаляет рецепт из избранного."""
        recipe = self.get_object()
        user = request.user

        favorite_exists = Favorite.objects.filter(
            author=user, recipe=recipe
        ).exists()

        if request.method == "POST":
            if favorite_exists:
                return Response(
                    {'error': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            favorite = Favorite.objects.create(author=user, recipe=recipe)
            serializer = FavoriteSerializer(
                favorite, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            if not favorite_exists:
                return Response(
                    {'error': 'Рецепт не найден в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Favorite.objects.filter(author=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=["post", "delete"], detail=True, url_path="shopping_cart",
            permission_classes=[IsAuthenticated])
    def shopping(self, request, pk):
        """Добавляет или удаляет рецепт в корзину."""
        recipe = self.get_object()
        user = request.user

        cart = ShoppingCard.objects.filter(
            author=user, recipe=recipe
        ).exists()

        if request.method == "POST":
            if cart:
                return Response(
                    {'error': 'Рецепт уже в корзине'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            favorite = ShoppingCard.objects.create(author=user, recipe=recipe)
            serializer = ShoppingListSerializer(
                favorite, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            if not cart:
                return Response(
                    {'error': 'Рецепт не найден в корзине'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            ShoppingCard.objects.filter(author=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=["get"], detail=False, url_path="download_shopping_cart")
    def get_shopping_cart(self, request):
        """Генерирует и возвращает список покупок в текстовом файле."""
        user = request.user
        ingredients = Ingredient.objects.filter(
            recipe_amounts__recipe__shopping__author=user
        ).annotate(
            total_amount=Sum('recipe_amounts__amount')
        ).values(
            'name', 'measurement_unit', 'total_amount'
        ).order_by('name')

        if not ingredients:
            return Response(
                {"detail": "Корзина пуста"},
                status=status.HTTP_400_BAD_REQUEST
            )

        response = HttpResponse(
            content_type='text/plain; charset=utf-8'
        )
        filename = 'attachment; filename="shopping_list.txt"'
        response['Content-Disposition'] = filename

        lines = [
            "=" * 50,
            "СПИСОК ПОКУПОК",
            "=" * 50,
            f"Пользователь: {user.username}",
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "Ингредиенты:",
            "-" * 30,
        ]

        for i, ingredient in enumerate(ingredients, 1):
            name = ingredient['name']
            unit = ingredient['measurement_unit']
            amount = ingredient['total_amount']
            lines.append(f"{i:2}. {name} ({unit}): {amount}")

        lines.extend([
            "",
            "=" * 50,
            f"Всего ингредиентов: {len(ingredients)}",
            "=" * 50,
        ])
        response.write("\n".join(lines))
        return response
