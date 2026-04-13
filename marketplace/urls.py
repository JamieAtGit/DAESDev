from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/producer/', views.register_producer, name='register_producer'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/products/new/', views.product_create, name='product_create'),
    path('dashboard/products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('dashboard/products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:pk>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:pk>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:pk>/', views.cart_update, name='cart_update'),
    path('checkout/', views.checkout, name='checkout'),
    path('surplus/', views.surplus_list, name='surplus_list'),
    path('surplus/add/', views.surplus_add, name='surplus_add'),
    path('community/', views.community_list, name='community_list'),
    path('community/add/', views.community_add, name='community_add'),
    path('settlements/', views.settlements, name='settlements'),
    path('recalls/', views.recall_list, name='recall_list'),
    path('recalls/new/', views.recall_new, name='recall_new'),
    path('recalls/<int:pk>/', views.recall_detail, name='recall_detail'),
]
