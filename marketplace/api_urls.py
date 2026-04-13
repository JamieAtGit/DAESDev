from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import CategoryViewSet, ProductViewSet, OrderViewSet, SurplusProduceViewSet, CommunityPostViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('products', ProductViewSet, basename='product')
router.register('orders', OrderViewSet, basename='order')
router.register('surplus', SurplusProduceViewSet, basename='surplus')
router.register('community', CommunityPostViewSet, basename='community')

urlpatterns = [
    path('', include(router.urls)),
]
