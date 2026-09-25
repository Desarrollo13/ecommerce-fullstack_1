from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.api.serializers import (
    CartItemInputSerializer,
    CartItemQuantitySerializer,
    CartItemSerializer,
    CartSerializer,
)
from cart.models import Cart, CartItem
from products.models import Product


def get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CartSerializer(get_cart(request.user)).data)


class CartItemCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CartItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            product = Product.objects.select_for_update().get(
                pk=serializer.validated_data["product"].pk
            )
            if not product.is_active:
                return Response(
                    {"product_id": ["This product is not available."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            cart = get_cart(request.user)
            item = CartItem.objects.select_for_update().filter(
                cart=cart, product=product
            ).first()
            quantity = serializer.validated_data["quantity"]
            total_quantity = quantity if item is None else item.quantity + quantity

            if total_quantity > product.stock:
                return Response(
                    {"quantity": ["The requested quantity exceeds available stock."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if item is None:
                item = CartItem.objects.create(
                    cart=cart, product=product, quantity=quantity
                )
                response_status = status.HTTP_201_CREATED
            else:
                item.quantity = total_quantity
                item.save(update_fields=("quantity", "updated_at"))
                response_status = status.HTTP_200_OK

        return Response(CartItemSerializer(item).data, status=response_status)


class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        serializer = CartItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            item = get_object_or_404(
                CartItem.objects.select_for_update(), cart=get_cart(request.user), pk=pk
            )
            product = Product.objects.select_for_update().get(pk=item.product_id)
            quantity = serializer.validated_data["quantity"]

            if quantity > product.stock:
                return Response(
                    {"quantity": ["The requested quantity exceeds available stock."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            item.quantity = quantity
            item.save(update_fields=("quantity", "updated_at"))

        return Response(CartItemSerializer(item).data)

    def delete(self, request, pk):
        item = get_object_or_404(CartItem, cart=get_cart(request.user), pk=pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
