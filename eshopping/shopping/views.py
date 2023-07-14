import cloudinary
from cloudinary import uploader
from django.db import IntegrityError
from django.db.models.functions import TruncMonth, TruncYear
from django.shortcuts import render
from django.http import HttpResponse
from .models import Category, Product, User, Order, Cart, CartDetail, Like, ProductReview, OrderDetail, Business, Shop, \
    Color, Size, Payment
from rest_framework import viewsets, permissions, generics, parsers, status, serializers

from .perms import ReviewOwner, IsBusiness, IsBusinessOwner, IsShopOwner
from .serializers import CategorySerializer, ProductSerializer, UserSerializer, GroupSerializer, OrderSerializer, \
    CartSerializer, AuthorizeProductDetailSerializer, ProductReviewSerializer, OrderDetailSerializer, \
    BusinessSerializer, ShopSerializer, ColorSerializer, SizeSerializer, CartDetailSerializer, PaymentSerializer, \
    LikeSerializer, OrderDetailDeserializer, StatsSerializer
from .paginators import ProductsPagination, CommentPagination
from django.contrib.auth.models import Group
from rest_framework.decorators import action, api_view
from rest_framework.views import Response
from django.db.models import Q, F, Count, Sum
from PIL import Image


class CategoryViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Category.objects.filter(active = True)
    serializer_class = CategorySerializer


class ProductViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView, generics.CreateAPIView,
                     generics.UpdateAPIView):
    queryset = Product.objects.filter(active = True)
    serializer_class = ProductSerializer
    pagination_class = ProductsPagination
    parser_classes = [parsers.MultiPartParser]

    def get_serializer_class(self):
        if self.request.user.is_authenticated:
            return AuthorizeProductDetailSerializer

        return self.serializer_class

    def get_permissions(self):
        if self.action in ['add_to_cart', 'like', 'review', 'get_like']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['create']:
            return [permissions.IsAuthenticated(), IsBusiness()]
        # elif self.action in ['update', 'partial_update']:
        #     return [permissions.IsAuthenticated(), IsBusiness(), IsShopOwner()]
        return [permissions.AllowAny()]

    def filter_queryset(self, queryset):
        q = queryset
        if self.action.__eq__('list'):
            kw = self.request.query_params.get('kw')
            category = self.request.query_params.get('category')
            min_price = self.request.query_params.get('min_price')
            max_price = self.request.query_params.get('max_price')
            sort_by = self.request.query_params.get('sort_by')
            if kw:
                q = q.filter(Q(shop__name__icontains = kw) | Q(name__icontains = kw))
            if min_price and max_price:
                q = q.filter(price__range = (min_price, max_price))
                q = q.annotate(
                    discounted_price = F('price') - F('price') * F('discount') / 100,
                ).filter(discounted_price__range = (min_price, max_price)).order_by('name')
            elif min_price:
                q = q.annotate(
                    discounted_price = F('price') - F('price') * F('discount') / 100,
                ).filter(discounted_price__gte = min_price).order_by('name')
            elif max_price:
                q = q.annotate(
                    discounted_price = F('price') - F('price') * F('discount') / 100,
                ).filter(discounted_price__lte = max_price).order_by('name')
            if sort_by:
                q = q.order_by(sort_by)
            if category:
                q = q.filter(category = category)
        return q

    def create(self, request, *args, **kwargs):
        # lấy thông tin từ request
        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)

        data = request.data
        colors = data.pop("colors")
        sizes = data.pop("sizes")
        thumbnail = ''
        image = request.data.get('thumbnail')
        category = Category.objects.get(id = int(data.get('category')))
        shop = Shop.objects.get(business = request.user.id)
        # kiểm tra ảnh nếu có thì lưu ảnh lên cloudinary
        if image:
            response = cloudinary.uploader.upload(image)
            thumbnail = response['url']

        product = Product.objects.create(name = data.get('name'), quantity = data.get('quantity'),
                                         price = data.get('price'),
                                         discount = data.get('discount'),
                                         category = category, thumbnail = thumbnail, shop = shop,
                                         description = data.get('description'))

        for size_data in sizes:
            size, _ = Size.objects.get_or_create(name = size_data)
            product.sizes.add(size)
        for color_data in colors:
            color, _ = Color.objects.get_or_create(name = color_data)
            product.colors.add(color)
        product.save()
        return Response(ProductSerializer(product, context = {'request': request}).data,
                        status = status.HTTP_201_CREATED)

    @action(methods = ['post'], detail = True, url_path = "add-to-cart")
    def add_to_cart(self, request, pk):
        try:
            p = self.get_object()
            quantity = request.data.get('quantity', 1)
            product = Product.objects.filter(id = pk).get()
            if request.data.get('size') is None or request.data.get('color') is None:
                return Response(data = {"message": 'Có lỗi xảy ra không thể thêm sản phẩm'},
                                status = status.HTTP_400_BAD_REQUEST)
            if int(quantity) > product.quantity:
                return Response(data = {'message': 'Quá số lượng cho phép'})
            else:
                cart = Cart.objects.filter(user_id = request.user).first()
                if not cart:
                    cart = Cart.objects.create(user = request.user)

                cart_detail = CartDetail.objects.filter(colors = request.data.get('color'),
                                                        sizes = request.data.get('size'),
                                                        product = product,
                                                        cart = cart).first()
                if cart_detail is None:
                    try:
                        cart_detail = CartDetail.objects.create()
                        cart_detail.sizes = Size.objects.filter(id = request.data.get('size')).first()
                        cart_detail.colors = Color.objects.filter(id = request.data.get('color')).first()
                        cart_detail.cart = cart
                        cart_detail.product = p
                        cart_detail.quantity += int(request.data.get('quantity', 1))
                    except:
                        cart_detail.delete()
                else:
                    cart_detail.quantity += int(request.data.get('quantity', 1))

                cart_detail.save()
                return Response(data = {'message': 'Thêm sản phẩm thành công'}, status = status.HTTP_201_CREATED)
        except IntegrityError as e:
            return Response(data = {"message": 'Có lỗi xảy ra không thể thêm sản phẩm'},
                            status = status.HTTP_400_BAD_REQUEST)

    @action(methods = ['post'], detail = True, url_path = 'like')
    def like(self, request, pk):

        l, created = Like.objects.get_or_create(user_id = request.user, product_id = self.get_object())
        if not created:
            l.active = not l.active
        l.save()
        # like = Like.objects.get(user_id = request.user, product_id = pk)
        # if not like:
        #     like = Like.objects.create(user = request.user, product = self.get_object(), active = True)
        #     like.save()

        return Response(data = LikeSerializer(l, context = {'request': request}).data, status = status.HTTP_200_OK)

    @action(methods = ['get'], detail = True, url_path = 'get-like')
    def get_like(self, request, pk):
        like = Like.objects.get(user_id = request.user, product_id = pk)

        return Response(data = LikeSerializer(like, context = {'request': request}).data, status = status.HTTP_200_OK)

    @action(methods = ['post'], detail = True, url_path = 'review')
    def review(self, request, pk):
        try:
            product = Product.objects.get(id = pk)
            data = request.data
            review = ProductReview(product = product, user = request.user)
            review.rating = data.get('rating')
            review.comment = data.get('comment')
            review.save()

            return Response(data = ProductReviewSerializer(review, context = {'request': request}).data,
                            status = status.HTTP_201_CREATED)
        except:
            return Response(data = {"message": "Đã có lỗi xảy ra"}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods = ['get'], detail = True, url_path = 'list-review')
    def list_review(self, request, pk):
        try:
            product = Product.objects.get(id = pk)
            reviews = ProductReview.objects.filter(active = True, product = product).order_by('-created_date')
            paginator = CommentPagination()
            list_review = paginator.paginate_queryset(reviews, request)

            return paginator.get_paginated_response(
                ProductReviewSerializer(list_review, many = True, context = {'request': request}).data
            )

        except:
            pass
            # return Response(data = {"message": "Đã có lỗi xảy ra"}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductCompareViewSet(viewsets.ViewSet, generics.ListAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.filter(active = True)

    def filter_queryset(self, queryset):
        if self.action.__eq__('list'):
            q = queryset
            product1_id = self.request.query_params.get('product1_id')
            product = Product.objects.get(id = product1_id)
            q = q.filter(category = product.category).exclude(id = product.id)
            # q = q.filter(id = product1_id)
        return q


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView,
                  generics.RetrieveAPIView, generics.ListAPIView):
    queryset = User.objects.filter(is_active = True)
    serializer_class = UserSerializer
    parser_classes = [parsers.MultiPartParser, ]

    def get_permissions(self):
        if self.action in ['current_user']:
            return [permissions.IsAuthenticated()]

        return [permissions.AllowAny()]

    @action(methods = ['get', 'put'], detail = False, url_path = 'current-user')
    def current_user(self, request):
        u = request.user
        if request.method.__eq__('PUT'):
            for k, v in request.data.items():
                setattr(u, k, v)
            u.save()

        return Response(UserSerializer(u, context = {'request': request}).data)

    @action(detail = False, methods = ['post'])
    def logout(self, request):
        try:
            request.user.auth_token.delete()
        except AttributeError:
            pass
        return Response({'message': 'User logged out successfully.'}, status = status.HTTP_200_OK)


class BusinessViewSet(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView,
                      generics.RetrieveAPIView):
    queryset = Business.objects.filter(is_active = True)
    serializer_class = BusinessSerializer
    parser_classes = [parsers.MultiPartParser, ]

    def get_permissions(self):
        if self.action in ['current_business']:
            return [permissions.IsAuthenticated()]

        return [permissions.AllowAny()]

    @action(methods = ['get', 'put'], detail = False, url_path = 'current-business')
    def current_business(self, request):
        u = Business.objects.get(pk = request.user.id)
        if request.method.__eq__('PUT'):
            for k, v in request.data.items():
                setattr(u, k, v)
            u.save()

        return Response(BusinessSerializer(u, context = {'request': request}).data, status = status.HTTP_200_OK)

    @action(methods = ['get'], detail = True, url_path = 'get-shop')
    def get_shop(self, request, pk):
        business = Business.objects.get(pk = pk)
        shop = Shop.objects.get(business = business)
        return Response(ShopSerializer(shop, context = {'request': request}).data, status = status.HTTP_200_OK)


# class GroupViewSet(viewsets.ViewSet, generics.ListAPIView):
#     queryset = Group.objects.all()
#     serializer_class = GroupSerializer


class OrderViewSet(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView, generics.RetrieveAPIView,
                   generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_permissions(self):
        if self.action in ['get_order_detail', 'create', 'get_user_order', 'partial_update', 'get_order_payment']:
            return [permissions.IsAuthenticated()]

        return [permissions.AllowAny()]

    @action(methods = ['get'], detail = False, url_path = 'get-user-order')
    def get_user_order(self, request):
        user = request.user
        order = Order.objects.filter(user = user).order_by('created_date')
        return Response(OrderSerializer(order, many = True, context = {'request': request}).data,
                        status = status.HTTP_200_OK)

    @action(methods = ['get'], detail = True, url_path = 'order-detail')
    def get_order_detail(self, request, pk):
        order = Order.objects.get(pk = pk)
        try:
            order_details = OrderDetail.objects.filter(order = order).order_by('created_date')
            if order_details:
                return Response(
                    OrderDetailDeserializer(order_details, many = True, context = {'request': request}).data,
                    status = status.HTTP_200_OK)
            return Response(status = status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response(data = {"message": "Có lỗi xảy ra"}, status = status.HTTP_502_BAD_GATEWAY)

    @action(methods = ['get'], detail = True, url_path = 'get-order-payment')
    def get_order_payment(self, request, pk):
        payment = Payment.objects.get(order = pk)
        return Response(PaymentSerializer(payment, context = {'request': request}).data, status = status.HTTP_200_OK)


    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data = request.data)
            serializer.is_valid(raise_exception = True)

            order_data = serializer.validated_data.copy()
            order_details_data = order_data.pop('order_details')
            payment_method = order_data.pop('payment_method')
            payment_status = order_data.pop('payment_status')

            order = Order.objects.create(**order_data, user = request.user)
            order.save()

            payment = Payment.objects.create(order = order, user = request.user, payment_method = payment_method,
                                             payment_status = payment_status, total_amount = order.total_amount)
            payment.save()
            for order_detail_data in order_details_data:
                OrderDetail.objects.create(order_id = order.id, **order_detail_data)

            # serializer = self.get_serializer(order)
            # headers = self.get_success_headers(serializer.data)
            return Response(data = OrderSerializer(order, context = {'request': request}).data,
                            status = status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            return Response(data = {"message": e.detail}, status = status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(data = {"message": "Có lỗi xảy ra"}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderDetailViewSet(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView):
    queryset = OrderDetail.objects.all()
    serializer_class = OrderDetailSerializer


class CartViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer

    def get_permissions(self):
        if self.action in ['get_cart_detail', ]:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    @action(methods = ['get'], detail = False, url_path = "cart-detail")
    def get_cart_detail(self, request):
        cart = Cart.objects.get(user = request.user)
        cart_detail = CartDetail.objects.filter(cart = cart)
        return Response(data = CartDetailSerializer(cart_detail, many = True, context = {'request': request}).data,
                        status = status.HTTP_200_OK)


class CartDetailViewSet(viewsets.ViewSet, generics.ListAPIView, generics.UpdateAPIView, generics.DestroyAPIView):
    queryset = CartDetail.objects.all()
    serializer_class = CartDetailSerializer

    def get_permissions(self):
        if self.action in ['destroy', 'update']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]


class ProductReviewViewSet(viewsets.ViewSet, generics.DestroyAPIView, generics.UpdateAPIView):
    queryset = ProductReview.objects.filter(active = True)
    serializer_class = ProductReviewSerializer
    permission_classes = [ReviewOwner, ]


class ShopViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.ListAPIView, generics.RetrieveAPIView,
                  generics.RetrieveUpdateDestroyAPIView):
    queryset = Shop.objects.filter(active = True)
    serializer_class = ShopSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated(), IsBusiness()]
        elif self.action in ['update']:
            return [permissions.IsAuthenticated(), IsBusiness(), IsBusinessOwner()]
        return [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data = request.data)
            serializer.is_valid(raise_exception = True)
            shop_data = serializer.validated_data.copy()

            if Shop.objects.filter(business = request.user).exists():
                return Response(data = {"message": "Mỗi doanh nghiệp/người bán chỉ được tạo 1 shop"},
                                status = status.HTTP_406_NOT_ACCEPTABLE)

            else:
                business = Business.objects.get(id = request.user.id)
                shop = Shop.objects.create(**shop_data)
                shop.business = business
                shop.is_active = True
                shop.save()
                return Response(data = {"message": "Success"}, status = status.HTTP_201_CREATED)

        except serializers.ValidationError as e:
            return Response(data = {"message": e.detail}, status = status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(data = {"message": "Có lỗi xảy ra"}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data = request.data)
            serializer.is_valid(raise_exception = True)
            shop_data = serializer.validated_data.copy()

            business = Business.objects.get(id = request.user.id)
            shop = Shop.objects.update(**shop_data, business = business)
            # shop.is_active = True
            # shop.save()
            return Response(data = {"message": "Success"}, status = status.HTTP_201_CREATED)


        except serializers.ValidationError as e:
            return Response(data = {"message": e.detail}, status = status.HTTP_400_BAD_REQUEST)
        # except Exception:
        #     return Response(data = {"message": "Có lỗi xảy ra"}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods = ['get'], detail = True, url_path = 'get-products')
    def get_products(self, request, pk):
        shop = Shop.objects.get(pk = pk)
        products = Product.objects.filter(shop = shop)
        serializer = ProductSerializer(products)
        return Response(ProductSerializer(products, many = True, context = {'request': request}).data,
                        status = status.HTTP_200_OK)


class StatsViewSet(viewsets.ViewSet):
    serializer_class = StatsSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail = False, methods = ['get'], url_path = 'stats-count')
    def stats_count(self, request):
        valid_statuses = ['created', 'confirm', 'shipped', 'delivered']
        total_amount = Order.objects.filter(status__in = valid_statuses).aggregate(Sum('total_amount'))[
                           'total_amount__sum'] or 0
        user_count = User.objects.count()
        order_count = Order.objects.count()
        product_count = Product.objects.count()
        data = {
            'total_amount': total_amount, 'user_count': user_count, 'order_count': order_count,
            'product_count': product_count
        }

        return Response(data = data, status = status.HTTP_200_OK)

    @action(detail = False, methods = ['get'], url_path = 'order-by-month')
    def order_by_month(self, request):
        order_by_month = Order.objects.annotate(month = TruncMonth('created_date')) \
            .values('month') \
            .annotate(total_amount = Sum('total_amount', filter = ~Q(status = 'cancelled')),
                      total_orders = Count('id', filter = ~Q(status = 'cancelled')),
                      canceled_orders = Count('id', filter = Q(status = 'cancelled')), ) \
            .order_by('month')
        response_data = {
            'data': list(order_by_month),
        }
        return Response(data = response_data, status = status.HTTP_200_OK)


class ColorsViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer


class SizesViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer


class PaymentViewSet(viewsets.ViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer



