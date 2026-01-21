from datetime import datetime

from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.models import Follow, Ingredient, Recipe, Tag, User

from .filers import IngredientSearchFilter, RecipeFilter
from .pagination import FoodgramPageNumberPagination
from .permissions import IsAuthorOrReadOnlyPermission
from .serializers import (AvatarSerializer, FavoriteActionSerializer,
                          FavoriteSerializer, FollowActionSerializer,
                          FollowSerializer, IngredientSerializer,
                          RecipeReadSerializer, RecipeWriteSerializer,
                          ShoppingCardActionSerializer, ShoppingListSerializer,
                          TagSerializer, UserSerializer)


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
    filter_backends = [IngredientSearchFilter]
    search_fields = ['^name']


class UserViewSet(DjoserUserViewSet):
    """ViewSet для работы с пользователями."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'post', 'delete', 'put']
    pagination_class = FoodgramPageNumberPagination

    def get_permissions(self):
        """
        Настройка permissions:
        - Список пользователей и просмотр профиля: AllowAny
        - Создание пользователя: AllowAny
        - Обновление/удаление: IsAuthenticated
        - Кастомные actions (me, subscribe и т.д.): IsAuthenticated
        """
        if self.action in ['list', 'retrieve', 'create']:
            return [AllowAny()]
        elif self.action in ['me', 'my_avatar', 'subscribe', 'subscriptions']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]

    @action(
        methods=["put", "delete"],
        detail=False,
        url_path="me/avatar",
    )
    def my_avatar(self, request):
        """Управляет аватаром текущего пользователя."""
        user = request.user
        if request.method == "PUT":
            serializer = AvatarSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)

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
        methods=["post", "delete"],
        detail=True,
        url_path="subscribe",
    )
    def subscribe(self, request, id=None):
        user = request.user
        recipes_limit = request.query_params.get('recipes_limit')

        if request.method == 'POST':
            valid_serializer = FollowActionSerializer(
                data={}, context={'request': request, 'view': self})
            valid_serializer.is_valid(raise_exception=True)
            following = valid_serializer.context['following']
            Follow.objects.create(user=user, following=following)
            serializer = FollowSerializer(
                following,
                context={'request': request, 'recipes_limit': recipes_limit}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            valid_serializer = FollowActionSerializer(
                data={}, context={'request': request, 'view': self})
            valid_serializer.is_valid(raise_exception=True)
            valid_serializer.context['follow'].delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=["get"],
        detail=False,
        url_path="subscriptions",
        serializer_class=FollowSerializer,
        pagination_class=FoodgramPageNumberPagination
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
    pagination_class = FoodgramPageNumberPagination
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
        return self._handle_relation_action(
            request=request,
            pk=pk,
            action_serializer_class=FavoriteActionSerializer,
            response_serializer_class=FavoriteSerializer
        )

    @action(methods=["post", "delete"], detail=True, url_path="shopping_cart",
            permission_classes=[IsAuthenticated])
    def shopping(self, request, pk):
        """Добавляет или удаляет рецепт в корзину."""
        return self._handle_relation_action(
            request=request,
            pk=pk,
            action_serializer_class=ShoppingCardActionSerializer,
            response_serializer_class=ShoppingListSerializer
        )

    def _handle_relation_action(
            self, request, pk, action_serializer_class,
            response_serializer_class):
        """Универсальный обработчик для действий с отношениями."""
        action_serializer = action_serializer_class(
            data={},
            context={'request': request, 'view': self}
        )
        action_serializer.is_valid(raise_exception=True)

        if request.method == "POST":
            recipe = action_serializer.context['recipe']
            user = action_serializer.context['user']
            model_class = action_serializer_class.Meta.model_class
            relation = model_class.objects.create(
                author=user,
                recipe=recipe
            )
            result_serializer = response_serializer_class(
                relation,
                context={'request': request}
            )

            return Response(
                result_serializer.data,
                status=status.HTTP_201_CREATED
            )

        elif request.method == "DELETE":
            relation_instance = action_serializer.context['relation_instance']
            relation_instance.delete()

            return Response(
                status=status.HTTP_204_NO_CONTENT
            )

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
