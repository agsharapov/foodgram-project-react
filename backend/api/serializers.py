import base64

from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import serializers
from rest_framework.status import HTTP_400_BAD_REQUEST

from recipes.models import (Cart, Favorite, Ingredient, IngredientAmount,
                            Recipe, Tag)
from users.serializers import CustomUserSerializer


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ('name', 'color', 'slug',)
        read_only_fields = ('name', 'color', 'slug',)
        model = Tag


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ('name', 'unit',)
        read_only_fields = ('name', 'unit',)
        model = Ingredient


class IngredientAmountSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    unit = serializers.ReadOnlyField(source='ingredient.unit')

    class Meta:
        model = IngredientAmount
        fields = ('id', 'name', 'unit', 'amount')


class RecipeListSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    image = Base64ImageField()
    ingredients = IngredientAmountSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_cart = serializers.SerializerMethodField(read_only=True)

    def get_user(self):
        return self.context['request'].user

    def get_is_favorited(self, obj):
        user = self.get_user()
        return (
            user.is_authenticated and
            user.favorites.filter(recipe=obj).exists()
        )

    def get_is_in_cart(self, obj):
        user = self.get_user()
        try:
            return (
                user.is_authenticated and
                user.cart.recipes.filter(pk__in=(obj.pk,)).exists()
            )
        except Cart.DoesNotExist:
            return False

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'name', 'image',  'text',
            'ingredients', 'tags', 'time', 'pub_date',
            'is_favorited', 'is_in_cart',
        )


class AddIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientAmount
        fields = ('id', 'amount',)


class RecipeSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    ingredients = AddIngredientSerializer(many=True)
    author = CustomUserSerializer(read_only=True)
    image = Base64ImageField()

    def validate(self, data):
        if len(data.get('ingredients')) == 0:
            raise serializers.ValidationError(
                {'ingredients': 'Минимум 1 ингредиент.'}
            )
        ingredients = data.get('ingredients')
        ingredients_list = []
        for ingredient in ingredients:
            ingredient_id = ingredient.get('id')
            if ingredient_id in ingredients_list:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты не должны повторяться.'}
                )
            ingredients_list.append(ingredient_id)
            amount = ingredient.get('amount')
            if amount < 0.01:
                raise serializers.ValidationError(
                    {'amount': 'Минимальное значение — 0.01.'}
                )

        cooking_time = data.get('cooking_time')
        if cooking_time < 1:
            raise serializers.ValidationError(
                {'cooking_time': 'Минимальное значение — 1.'}
            )
        return data

    def validate_cart(self, model, user, pk):
        if model.objects.filter(user=user, recipe__id=pk).exists():
            raise serializers.ValidationError(
                detail='Рецепт уже добавлен.',
                code=HTTP_400_BAD_REQUEST
            )

    def validate_tags(self, data):
        tags = data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Минимум 1 тег.'}
            )
        tags_list = []
        for tag in tags:
            if tag in tags_list:
                raise serializers.ValidationError(
                    {'tags': 'Теги не должны повторяться.'}
                )
            tags_list.append(tag)

    @transaction.atomic
    def __create_ingredients_amounts__(self, ingredients, recipe):
        IngredientAmount.objects.bulk_create(
            [IngredientAmount(
                ingredient=Ingredient.objects.get(id=ingredient.get('id')),
                recipe=recipe,
                amount=ingredient.get('amount')
            ) for ingredient in ingredients]
        )

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.__create_ingredients_amounts__(
            recipe=recipe,
            ingredients=ingredients
        )
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.__create_ingredients_amounts__(
            recipe=instance,
            ingredients=ingredients
        )
        instance.save()
        return instance

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return RecipeListSerializer(instance,
                                    context=context).data

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'name', 'image',  'text',
            'ingredients', 'tags', 'time', 'pub_date',
        )


class ShortRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):

    def validate(self, data):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        recipe = data.get('recipe', None)
        if Favorite.objects.filter(user=request.user, recipe=recipe).exists():
            raise serializers.ValidationError(
                {'status': 'Рецепт уже есть в избранном.'}
            )
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return ShortRecipeSerializer(instance.recipe, context=context).data

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')


class CartSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return ShortRecipeSerializer(instance.recipe, context=context).data

    class Meta:
        model = Cart
        fields = ('user', 'recipe')
