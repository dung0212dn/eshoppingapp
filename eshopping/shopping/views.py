import cloudinary
from cloudinary import uploader
from django.shortcuts import render
from django.http import HttpResponse
from .models import Category, Product, User, Order, Cart, CartDetail, Like, ProductReview, OrderDetail, Business, Shop, \
    Color, Size
from rest_framework import viewsets, permissions, generics, parsers, status, serializers

from .perms import ReviewOwner, IsBusiness, IsBusinessOwner, IsShopOwner
from .serializers import CategorySerializer, ProductSerializer, UserSerializer, GroupSerializer, OrderSerializer, \
    CartSerializer, AuthorizeProductDetailSerializer, ProductReviewSerializer, OrderDetailSerializer, \
    BusinessSerializer, ShopSerializer
from .paginators import ProductsPagination, CommentPagination
from django.contrib.auth.models import Group
from rest_framework.decorators import action
from rest_framework.views import Response
from django.db.models import Q
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
        if self.action in ['add_to_cart', 'like', 'review']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['create']:
            return [permissions.IsAuthenticated(), IsBusiness()]
        elif self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsBusiness(), IsShopOwner()]
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
            elif min_price:
                q = q.filter(price__gte = min_price)
            elif max_price:
                q = q.filter(price__lte = max_price)
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

        product = Product.objects.create(name = data.get('name'), quantity = data.get('quantity'), price = 200000,
                                         discount = data.get('discount'),
                                         category = category, thumbnail = thumbnail, shop = shop, description = data.get('description'))

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
            product = Product.objects.filter(id = p.id).get()
            if quantity > product.quantity:
                return Response(data = {'message': 'Quá số lượng cho phép'})
            else:
                cart = Cart.objects.filter(user_id = request.user).first()
                if not cart:
                    cart = Cart.objects.create(user = request.user)

                cart_detail = CartDetail.objects.filter(colors = request.data.get('colors'),
                                                        sizes = request.data.get('sizes'),
                                                        product = p,
                                                        cart = cart).get()
                if not cart_detail:
                    cart_detail = CartDetail.objects.create()
                    cart_detail.sizes.add(request.data.get('sizes'))
                    cart_detail.colors.add(request.data.get('colors'))
                    cart_detail.cart = cart
                    cart_detail.product = p
                    cart_detail.quantity += request.data.get('quantity', 1)
                else:
                    cart_detail.quantity += request.data.get('quantity', 1)

                cart_detail.save()
                return Response(data = {'message': 'Thêm sản phẩm thành công'}, status = status.HTTP_201_CREATED)
        except Exception:
            return Response(data = {"message": 'Có lỗi xảy ra không thể thêm sản phẩm'})

    @action(methods = ['post'], detail = True, url_path = 'like')
    def like(self, request, pk):
        l, created = Like.objects.get_or_create(user = request.user, product = self.get_object())
        if not created:
            l.active = not l.active
        l.save()

        return Response(status = status.HTTP_200_OK)

    @action(methods = ['post'], detail = True, url_path = 'review')
    def review(self, request, pk):
        try:
            product = self.get_object()
            data = request.data
            review = ProductReview(product = product, user = request.user)
            review.rating = data.get('rating')
            review.comment = data.get('comment')
            review.save()

            return Response(data = {"message": "Thêm bình luận thành công"}, status = status.HTTP_201_CREATED)
        except:
            return Response(data = {"message": "Đã có lỗi xảy ra"}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods = ['get'], detail = True, url_path = 'list-review')
    def list_review(self, request, pk):
        try:
            product = self.get_object()
            reviews = ProductReview.objects.filter(active = True, product = product)
            paginator = CommentPagination()
            list_review = paginator.paginate_queryset(reviews, self.request)

            return Response(ProductReviewSerializer(list_review, many = True, context = {'request': request}).data,
                            status = status.HTTP_200_OK)

        except:
            return Response(data = {"message": "Đã có lỗi xảy ra"}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                  generics.RetrieveAPIView):
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


# class GroupViewSet(viewsets.ViewSet, generics.ListAPIView):
#     queryset = Group.objects.all()
#     serializer_class = GroupSerializer


class OrderViewSet(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView, generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_permissions(self):
        if self.action in ['get_order_detail', 'create']:
            return [permissions.IsAuthenticated()]

        return [permissions.AllowAny()]

    @action(methods = ['get'], detail = True, url_path = 'order-detail')
    def get_order_detail(self, request, pk):
        order = self.get_object()
        try:
            order_details = OrderDetail.objects.get(order = order)
            if order_details:
                return Response(OrderDetailSerializer(order_details, context = {'request': request}).data,
                                status = status.HTTP_200_OK)
            return Response(status = status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response(data = {"message": "Có lỗi xảy ra"}, status = status.HTTP_502_BAD_GATEWAY)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data = request.data)
            serializer.is_valid(raise_exception = True)

            order_data = serializer.validated_data.copy()
            order_details_data = order_data.pop('order_details')

            order = Order.objects.create(**order_data)
            order.save()
            for order_detail_data in order_details_data:
                OrderDetail.objects.create(order_id = order.id, **order_detail_data)

            # serializer = self.get_serializer(order)
            # headers = self.get_success_headers(serializer.data)
            return Response(data = {"message": "Success"}, status = status.HTTP_201_CREATED)
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


class StatsViewSet(viewsets.ViewSet):
    pass
