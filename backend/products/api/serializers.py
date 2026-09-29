from rest_framework import serializers

from products.models import Category, Product


class PublicProductSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()

    def get_is_available(self, product: Product) -> bool:
        return product.stock > 0

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "image",
            "category",
            "is_available",
            "created_at",
            "updated_at",
        ]


class PublicCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "created_at", "updated_at"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'price',
            'stock',
            'image',
            'is_active',
            'category',
            'created_at',
            'updated_at',
        ]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
