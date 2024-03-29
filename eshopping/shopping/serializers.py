import cloudinary
from django.db.models import Sum, Avg
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import (Category, Product, Payment, User, Color, Size, Shop, Business,
                     ShopReview, Like, ProductReview, Cart, CartDetail, Order, OrderDetail)
from django.contrib.auth.models import Group


#
# class ImageSerializer(serializers.ModelSerializer):
#     image = serializers.SerializerMethodField(source = 'image')
#
#     def get_image(self, course):
#         if course.image:
#             request = self.context.get('request')
#             return request.build_absolute_uri('/static/%s' % course.image.name) if request else ''


class UserSerializer(ModelSerializer):
    image = serializers.SerializerMethodField(source = 'avatar')

    # def get_image(self, user):
    #     if user.avatar:
    #         request = self.context.get('request')
    #         return request.build_absolute_uri('/static/%s' % user.avatar.name) if request else ''

    def get_image(self, user):
        if user.avatar:
            request = self.context.get('request')
            response = cloudinary.uploader.upload(user.avatar)
            return response['url']

    def create(self, validated_data):
        data = validated_data.copy()
        group = Group.objects.get(name = 'User')
        data.pop('groups', None)
        data.update({'is_active': True})
        permissions = data.pop('user_permissions', [])
        u = User.objects.create_user(**data)
        u.user_permissions.set(permissions)
        u.groups.add(group)
        return u

    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {
            'password': {'write_only': True},
            'avatar': {'write_only': True},
        }


class BusinessSerializer(ModelSerializer):
    image = serializers.SerializerMethodField(source = 'avatar')

    # def get_image(self, business):
    #     if business.avatar:
    #         request = self.context.get('request')
    #         return request.build_absolute_uri('/static/%s' % business.avatar.name) if request else ''
    def get_image(self, user):
        if user.avatar:
            request = self.context.get('request')
            response = cloudinary.uploader.upload(user.avatar)
            return response['url']

    def create(self, validated_data):
        data = validated_data.copy()
        group = Group.objects.get(name = 'Business')
        data.pop('groups', None)
        data.update({'is_active': True})
        u = Business(**data)
        u.set_password(u.password)
        u.save()
        u.groups.add(group)
        return u

    class Meta:
        model = Business
        fields = "__all__"
        extra_kwargs = {
            'password': {'write_only': True},
            'avatar': {'write_only': True},
        }


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class ColorSerializer(ModelSerializer):
    class Meta:
        model = Color
        fields = "__all__"


class SizeSerializer(ModelSerializer):
    class Meta:
        model = Size
        fields = "__all__"


class ShopSerializer(ModelSerializer):
    business = serializers.PrimaryKeyRelatedField(
        queryset = Business.objects.filter(is_active = True, status = 'confirmed'))

    class Meta:
        model = Shop
        fields = "__all__"
        extra_kwargs = {
            'business': {'write_only': True},
        }


class ProductSerializer(ModelSerializer):
    # image = serializers.SerializerMethodField(source = 'thumbnail')
    thumbnail = serializers.ImageField(use_url = False)
    colors = ColorSerializer(many = True, required = False)
    sizes = SizeSerializer(many = True, required = False)
    category = CategorySerializer(required = False)
    rating = serializers.SerializerMethodField()
    total_liked = serializers.SerializerMethodField()
    shop = ShopSerializer(required = False)

    def get_rating(self, obj):
        product_rating = ProductReview.objects.filter(product = obj).aggregate(Avg('rating'))['rating__avg']
        return product_rating

    def get_total_liked(self, obj):
        total_like = Like.objects.filter(product_id = obj, active = True).count()
        return total_like

    # def get_image(self, product):
    #     if product.thumbnail:
    #         request = self.context.get('request')
    #         return request.build_absolute_uri('/static/%s' % product.thumbnail.name) if request else ''

    class Meta:
        model = Product
        fields = ['id', 'name', 'quantity', 'price', 'discount', "thumbnail", "shop", "description", "colors", "sizes",
                  "category", 'rating', 'total_liked']


class ProductReviewSerializer(ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = ProductReview
        fields = "__all__"


class AuthorizeProductDetailSerializer(ProductSerializer):
    liked = serializers.SerializerMethodField()

    # product_reviews = serializers.PrimaryKeyRelatedField(queryset = ProductReview.objects.all())

    def get_liked(self, product):
        request = self.context.get('request')
        if request:
            return product.liked.filter(user_id = request.user).exists()

    def create(self, validated_data):
        sizes = validated_data.pop("sizes")
        colors = validated_data.pop("colors")
        product = Product.objects.create(**validated_data)
        for color_data in colors:
            color, _ = Color.objects.get_or_create(**color_data)
            product.colors.add(color)
        for size_data in sizes:
            size, _ = Size.objects.get_or_create(**size_data)
            product.sizes.add(size)
        product.save()
        return product

    class Meta:
        model = ProductSerializer.Meta.model
        fields = ProductSerializer.Meta.fields + ['liked']


class GroupSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = "__all__"


class OrderDetailSerializer(ModelSerializer):
    sizes = serializers.PrimaryKeyRelatedField(queryset = Size.objects.all())
    colors = serializers.PrimaryKeyRelatedField(queryset = Color.objects.all())
    product = serializers.PrimaryKeyRelatedField(queryset = Product.objects.filter(active = True))

    class Meta:
        model = OrderDetail
        fields = "__all__"


class OrderDetailDeserializer(ModelSerializer):
    sizes = SizeSerializer()
    colors = ColorSerializer()
    product = ProductSerializer()

    class Meta:
        model = OrderDetail
        fields = "__all__"


class OrderSerializer(ModelSerializer):
    order_details = OrderDetailSerializer(many = True, required = False)
    payment_method = serializers.CharField(write_only = True)
    payment_status = serializers.CharField(write_only = True)

    class Meta:
        model = Order
        fields = "__all__"
        extra_kwargs = {
            'order_details': {'read_only': True},
        }


class CartDetailSerializer(ModelSerializer):
    product = ProductSerializer()
    colors = ColorSerializer()
    sizes = SizeSerializer()

    class Meta:
        model = CartDetail
        fields = "__all__"


class CartSerializer(ModelSerializer):
    cart_detail = CartDetailSerializer(many = True)

    class Meta:
        model = Cart
        fields = "__all__"


class PaymentSerializer(ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class LikeSerializer(ModelSerializer):
    class Meta:
        model = Like
        fields = "__all__"


class StatsSerializer(ModelSerializer):
    user_count = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits = 10, decimal_places = 2)
    order_count = serializers.IntegerField()
