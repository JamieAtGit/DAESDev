from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Category, Product, Order, SurplusProduce, CommunityPost
from .serializers import CategorySerializer, ProductSerializer, OrderSerializer, SurplusProduceSerializer, CommunityPostSerializer


class IsProducerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'producer'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.producer == request.user.producer_profile


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsProducerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'farm_origin', 'producer__business_name']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Product.objects.select_related('producer', 'category').filter(is_active=True)
        category = self.request.query_params.get('category')
        organic = self.request.query_params.get('organic')
        if category:
            qs = qs.filter(category__slug=category)
        if organic in ('true', '1'):
            qs = qs.filter(is_organic=True)
        return qs

    def perform_create(self, serializer):
        serializer.save(producer=self.request.user.producer_profile)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my(self, request):
        if request.user.role != 'producer':
            return Response({'detail': 'Producer account required.'}, status=403)
        products = Product.objects.filter(producer=request.user.producer_profile).order_by('-created_at')
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)


class SurplusProduceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SurplusProduceSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return SurplusProduce.objects.filter(
            is_active=True,
            available_until__gte=timezone.now()
        ).select_related('product', 'product__producer').order_by('available_until')


class CommunityPostViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CommunityPostSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'content', 'producer__business_name']

    def get_queryset(self):
        qs = CommunityPost.objects.select_related('producer', 'product').order_by('-created_at')
        post_type = self.request.query_params.get('type')
        if post_type:
            qs = qs.filter(post_type=post_type)
        return qs
