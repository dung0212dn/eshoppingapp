from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.contrib import admin
from .models import Category, Product, Payment, User, Color, Size, Shop, Business, ShopReview, Like, ProductReview, \
    Cart, CartDetail, OrderDetail, Order
from django.utils.html import mark_safe
from django import forms


class CategoryForm(forms.ModelForm):
    description = forms.CharField(widget = CKEditorUploadingWidget)

    class Meta:
        model = Category
        fields = '__all__'


class CategoryAdmin(admin.ModelAdmin):
    form = CategoryForm


class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "created_date", "active", "price", "discount", 'quantity', 'thumbnail']
    readonly_fields = ["product_image"]

    def product_image(self, product):
        return mark_safe(
            "<img src='{thumbnail_url}' width='120' />".format(thumbnail_url = product.thumbnail.name))


class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "first_name", "last_name", "date_joined", "is_active", "username", 'avatar']
    readonly_fields = ["avatar"]
    readonly_fields = ('last_login', 'date_joined')

    def get_readonly_fields(self, request, obj = None):
        # Nếu request.user không phải là superuser thì readonly_fields sẽ được áp dụng
        if not request.user.is_superuser:
            return self.readonly_fields + ('is_superuser', 'groups', 'user_permissions')
        return self.readonly_fields


class OrderAdmin(admin.ModelAdmin):
    list_display = ["id"]


class ShopAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "business"]


class BusinessAdmin(UserAdmin):
    list_display = ["id", "first_name", "last_name", "date_joined", "is_active", "username", 'avatar']
    readonly_fields = ["avatar"]
    readonly_fields = ('last_login', 'date_joined')

    def get_readonly_fields(self, request, obj = None):
        # Nếu request.user không phải là superuser thì readonly_fields sẽ được áp dụng
        if not request.user.is_superuser:
            return self.readonly_fields + ('is_superuser', 'groups', 'user_permissions')
        return self.readonly_fields


# Register your models here.
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Payment)
admin.site.register(User, UserAdmin)
admin.site.register(Color)
admin.site.register(Size)
admin.site.register(Shop, ShopAdmin)
admin.site.register(Business, BusinessAdmin)
admin.site.register(ShopReview)
admin.site.register(Like)
admin.site.register(ProductReview)
admin.site.register(Cart)
admin.site.register(CartDetail)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderDetail)
