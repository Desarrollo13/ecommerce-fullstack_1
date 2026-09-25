from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import Cart, CartItem
from orders.api.serializers import OrderSerializer
from orders.models import Order, OrderItem
from products.models import Product


class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).prefetch_related("items")
        return Response(OrderSerializer(orders, many=True).data)

    def post(self, request):
        with transaction.atomic():
            try:
                cart = Cart.objects.select_for_update().get(user=request.user)
            except Cart.DoesNotExist:
                return Response(
                    {"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST
                )

            cart_items = list(
                CartItem.objects.select_for_update()
                .filter(cart=cart)
                .order_by("product_id")
            )
            if not cart_items:
                return Response(
                    {"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST
                )

            products = {
                product.pk: product
                for product in Product.objects.select_for_update()
                .filter(pk__in=[item.product_id for item in cart_items])
                .order_by("pk")
            }

            for item in cart_items:
                product = products.get(item.product_id)
                if product is None or not product.is_active:
                    return Response(
                        {"detail": "A cart product is no longer available."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if item.quantity > product.stock:
                    return Response(
                        {"detail": "A cart product no longer has enough stock."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            total = sum(
                (
                    products[item.product_id].price * item.quantity
                    for item in cart_items
                ),
                Decimal("0.00"),
            )
            order = Order.objects.create(user=request.user, total=total)
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=products[item.product_id],
                        product_name=products[item.product_id].name,
                        unit_price=products[item.product_id].price,
                        quantity=item.quantity,
                        line_total=products[item.product_id].price * item.quantity,
                    )
                    for item in cart_items
                ]
            )

            for item in cart_items:
                product = products[item.product_id]
                product.stock -= item.quantity
                product.save(update_fields=("stock", "updated_at"))

            CartItem.objects.filter(pk__in=[item.pk for item in cart_items]).delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.prefetch_related("items"), pk=pk, user=request.user
        )
        return Response(OrderSerializer(order).data)
