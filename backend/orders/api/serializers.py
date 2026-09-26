from rest_framework import serializers

from orders.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product",
            "product_name",
            "unit_price",
            "quantity",
            "line_total",
        )


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "shipping_address",
            "payment_method",
            "payment_status",
            "total",
            "items",
            "created_at",
            "updated_at",
        )


class CheckoutSerializer(serializers.Serializer):
    shipping_address = serializers.CharField(max_length=500)
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)


class PaymentStatusSerializer(serializers.Serializer):
    payment_status = serializers.ChoiceField(choices=Order.PaymentStatus.choices)
