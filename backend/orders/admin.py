from django.contrib import admin

from orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "product_name", "unit_price", "quantity", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "payment_method",
        "payment_status",
        "payment_provider",
        "total",
        "created_at",
    )
    list_filter = ("status", "payment_method", "payment_status")
    search_fields = ("user__email", "user__username")
    inlines = (OrderItemInline,)
