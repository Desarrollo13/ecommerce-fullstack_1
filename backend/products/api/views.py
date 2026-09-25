from rest_framework import generics
from rest_framework.permissions import IsAdminUser

from products.api.serializers import (
    CategorySerializer,
    ProductSerializer,
    PublicCategorySerializer,
    PublicProductSerializer,
)
from products.models import Category, Product


class ProductListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return []

    def get_queryset(self):
        if self.request.user.is_staff:
            return Product.objects.all()
        return Product.objects.filter(is_active=True, category__is_active=True)

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return ProductSerializer
        return PublicProductSerializer


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAdminUser()]
        return []

    def get_queryset(self):
        if self.request.user.is_staff:
            return Product.objects.all()
        return Product.objects.filter(is_active=True, category__is_active=True)

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return ProductSerializer
        return PublicProductSerializer


class CategoryListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return []

    def get_queryset(self):
        if self.request.user.is_staff:
            return Category.objects.all()
        return Category.objects.filter(is_active=True)

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return CategorySerializer
        return PublicCategorySerializer


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAdminUser()]
        return []

    def get_queryset(self):
        if self.request.user.is_staff:
            return Category.objects.all()
        return Category.objects.filter(is_active=True)

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return CategorySerializer
        return PublicCategorySerializer
