from rest_framework import generics
from rest_framework.permissions import IsAdminUser


from products.models import Product,Category
from products.api.serializers import ProductSerializer,CategorySerializer


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # protego las acciones de escritura con get_permissions
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return[]
        
    
class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer  
    # voy proteger tambien las acciones de escritura
    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return  [IsAdminUser()]
        return [] 


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    def get_permissions(self):
        if self.request.method =="POST":
            return [IsAdminUser()]
        return[]
    
class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer  
    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAdminUser()]

        return []  