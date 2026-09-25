from django.urls import path

from products.api.views import ProductListCreateView,ProductDetailView,CategoryListCreateView,CategoryDetailView


urlpatterns = [
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path("categories/", CategoryListCreateView.as_view()),
    path("categories/<int:pk>/", CategoryDetailView.as_view()),
    
]