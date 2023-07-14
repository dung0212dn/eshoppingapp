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
router.register('cart-detail', viewset = views.CartDetailViewSet)
router.register('product-review', viewset = views.ProductReviewViewSet)
router.register('order-detail', viewset = views.OrderDetailViewSet)
router.register('business', viewset = views.BusinessViewSet)
router.register('shop', viewset = views.ShopViewSet)
# router.register(r'product-compare', viewset = views.ProductCompareViewSet, basename='product-search')
router.register('colors', viewset = views.ColorsViewSet)
router.register('sizes', viewset = views.SizesViewSet)
router.register('payment', viewset = views.PaymentViewSet)
router.register('stats', viewset = views.StatsViewSet, basename = 'stats')
# router.register('reset-password', viewset = views.PasswordResetViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
