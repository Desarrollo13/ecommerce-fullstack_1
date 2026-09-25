from django.db.models.deletion import ProtectedError
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

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

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=("is_active", "updated_at"))


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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {"detail": "Category cannot be deleted while it has products."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
