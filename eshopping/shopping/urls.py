from django.contrib import admin
from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('categories', viewset = views.CategoryViewSet)
router.register('products', viewset = views.ProductViewSet)
router.register('users', viewset = views.UserViewSet)
# router.register('group', viewset = views.GroupViewSet)
router.register('order', viewset = views.OrderViewSet)
router.register('cart', viewset = views.CartViewSet)
router.register('product-review', viewset = views.ProductReviewViewSet)
router.register('order-detail', viewset = views.OrderDetailViewSet)
router.register('business', viewset = views.BusinessViewSet)
router.register('shop', viewset = views.ShopViewSet)
router.register(r'product-compare', viewset = views.ProductCompareViewSet, basename='product-search')

urlpatterns = [
    path('', include(router.urls)),
]
