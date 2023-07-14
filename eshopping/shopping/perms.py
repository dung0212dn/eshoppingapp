from rest_framework import permissions
from rest_framework.permissions import BasePermission

from .models import Business, Shop, Product, CartDetail, Cart


class ReviewOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, review):
        return request.user and request.user == review.user


class IsBusiness(BasePermission):
    def has_permission(self, request, view):
        # Kiểm tra nếu user là doanh nghiệp
        return request.user.groups.filter(name = 'Business').exists()


class IsBusinessOwner(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if request.method == 'PUT' or request.method == 'DELETE' or request.method == 'PATCH':  # chỉ kiểm tra khi request là PUT
            business = Business.objects.get(id = request.user.id)
            shop_id = view.kwargs.get('pk')  # lấy id sản phẩm từ url
            shop = Shop.objects.get(pk = shop_id)
            return shop.business == business  # kiểm tra user có phải là người tạo sản phẩm hay không
        return True  # cho phép các request khác (GET, POST)


class IsShopOwner(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if request.method == 'PUT' or request.method == 'DELETE' or request.method == 'PATCH':
            user = request.user
            business = Business.objects.get(id = user.id)
            shop = Shop.objects.get(business = business.id)
            product_id = view.kwargs.get('pk')  # lấy id sản phẩm từ url
            product = Product.objects.get(pk = product_id)
            return product.shop == shop.id
        return True

