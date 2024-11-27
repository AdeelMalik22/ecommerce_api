from django_filters import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from .models import Product, ShoppingCart, CartItem, Order, OrderItem
from .serializers import ProductSerializer, ShoppingCartSerializer, CartItemSerializer, OrderSerializer
from decimal import Decimal

# Product ViewSet
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    search_fields = ['category']


# ShoppingCart ViewSet
class ShoppingCartViewSet(viewsets.ModelViewSet):
    queryset = ShoppingCart.objects.all()
    serializer_class = ShoppingCartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ShoppingCart.objects.filter(user=self.request.user)

    @action(methods=['post'], detail=False, permission_classes=[IsAuthenticated])
    def add_to_cart(self, request):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        cart, created = ShoppingCart.objects.get_or_create(user=request.user)
        cart.save()
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={'quantity': quantity, 'price': product.price}
        )

        if not item_created:
            cart_item.quantity += int(quantity)
        cart_item.price = cart_item.quantity * product.price
        cart_item.save()

        cart.total_price = sum(item.quantity * item.price for item in cart.cartitem_set.all())
        cart.save()

        return Response({'message': 'Product added to cart'}, status=status.HTTP_201_CREATED)


    @action(methods=['post'], detail=False, permission_classes=[IsAuthenticated])
    def order_cart(self, request):
        user = request.user

        try:
            cart = ShoppingCart.objects.get(user=user)
            if cart.cartitem_set.count() == 0:
                return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

            order = Order.objects.create(user=user, total_price=cart.total_price, status='Pending')

            for item in cart.cartitem_set.all():
                OrderItem.objects.create( order=order,product=item.product,quantity=item.quantity,price=item.price)

            cart.cartitem_set.all().delete()
            cart.total_price = 0
            cart.save()

            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ShoppingCart.DoesNotExist:
            return Response({'error': 'Cart does not exist'}, status=status.HTTP_404_NOT_FOUND)


# Order ViewSet
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
