import datetime

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, PermissionsMixin
from django.core.validators import *
from django.utils.translation import gettext_lazy as _
from ckeditor.fields import RichTextField


# Create your models here.


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add = True)
    updated_date = models.DateTimeField(auto_now = True)
    description = RichTextField(null = True)
    active = models.BooleanField(default = True)

    class Meta:
        abstract = True


class User(AbstractUser):
    avatar = models.ImageField(upload_to = "avatar/%Y/%m")



class Category(BaseModel):
    name = models.CharField(max_length = 255, null = False, unique = True)

    # slug = models.CharField(max_length = 255, validators = validate_slug)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Categories'
        verbose_name_plural = 'Categories'


# Sản phẩm:  Tên sản phẩm, số lượng, thumnail sản phẩm, giá cả, khuyến mãi, kích thước, màu sắc( nếu có), loại sản phẩm(fk), cửa hàng(fk)
class Product(BaseModel):
    name = models.CharField(max_length = 255, null = False)
    quantity = models.IntegerField(validators = [MinValueValidator(0)], null = False)
    thumbnail = models.ImageField(upload_to = "shopping/%Y/%m", default = None)
    price = models.IntegerField(validators = [MinValueValidator(0)], null = False)
    discount = models.IntegerField(validators = [MinValueValidator(0), MaxValueValidator(100)])
    sizes = models.ManyToManyField('size', blank = True, related_name = "products")
    colors = models.ManyToManyField("color", blank = True, related_name = "products")
    category = models.ForeignKey(Category, on_delete = models.PROTECT)
    shop = models.ForeignKey("shop", on_delete = models.SET_NULL, null = True, related_name = 'products')

    # slug = models.CharField(max_length = 255, validators = validate_slug)

    def __str__(self):
        return self.name


# Màu sắc: Tên màu, mô tả
class Color(models.Model):
    name = models.CharField(max_length = 255)

    def __str__(self):
        return self.name


class Size(models.Model):
    name = models.CharField(max_length = 25)

    def __str__(self):
        return self.name


# Yêu thích: Người thích, sản phẩm được thích
class Like(BaseModel):
    user_id = models.ForeignKey(User, on_delete = models.CASCADE, related_name = "liked")
    product_id = models.ForeignKey(Product, on_delete = models.CASCADE, related_name = "liked")


# Doanh nghiệp: Tên doanh nghiệp, địa chỉ kinh doanh, mã số thuế, số điện thoại, loại hàng sẽ bán.
class Business(User):
    STATUS_CHOICES = (
        ('confirmed', 'Confirmed'),
        ('unconfirmed', 'Unconfirmed'),
    )

    business_name = models.CharField(max_length = 255, null = False)
    category = models.ForeignKey('category', on_delete = models.SET_NULL, null = True)
    address = models.CharField(max_length = 255, null = False)
    phone = models.CharField(max_length = 10, null = False)
    tax_code = models.CharField(max_length = 255, null = False)
    status = status = models.CharField(max_length = 20, choices = STATUS_CHOICES, default = 'unconfirmed')

    class Meta:
        verbose_name = 'Business'
        verbose_name_plural = 'Business'


# -	Đơn hàng: họ tên, email, số điện thoại của người đặt hàng, địa chỉ giao hàng, trạng thái đơn hàng, ngày đặt đơn
class Order(BaseModel):
    STATUS_CHOICES = (
        ('created', 'Created'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )

    name = models.CharField(max_length = 255, null = False)
    email = models.EmailField(max_length = 255)
    phone = models.CharField(max_length = 10, null = False)
    address = models.CharField(max_length = 255, null = False)
    total_amount = models.IntegerField(validators = [MinValueValidator(0)], null = False)
    status = models.CharField(max_length = 20, choices = STATUS_CHOICES, default = 'created')

    def __str__(self):
        return "Đơn hàng số " + str(self.id)


# -	Chi tiết đơn hàng: Tên sản phẩm, giá sản phẩm, khuyến mãi( nếu có), số lượng sản phẩm, màu sắc, kích thước( nếu có), đơn hàng(fk)
class OrderDetail(BaseModel):
    product = models.ForeignKey(Product, on_delete = models.SET_NULL, null = True)
    order = models.ForeignKey(Order, on_delete = models.SET_NULL, null = True, related_name = "order_detail")
    price = models.IntegerField(validators = [MinValueValidator(0)], null = False)
    discount = models.IntegerField(validators = [MinValueValidator(0), MaxValueValidator(100)])
    sizes = models.ForeignKey('size', blank = True, related_name = "order_details", on_delete = models.CASCADE, default = 1)
    colors = models.ForeignKey("color", blank = True, related_name = "order_details", on_delete = models.CASCADE, default = 1)
    quantity = models.IntegerField(validators = [MinValueValidator(0)], null = False)

    class Meta:
        unique_together = ('product', 'order')


# Thanh toán: Số tiền thanh toán, phương thức thanh toán, trạng thái thanh toán, đơn hàng(fk)


class Payment(BaseModel):
    class PaymentMethod(models.TextChoices):
        COD = "COD", _('Cash on Deliver')
        PAYPAL = 'PAYPAL', _("Paypal")
        BANK_TRANSFER = 'BANK_TRANSFER', _("Bank Transfer")
        MOMO = 'MOMO', _("Momo")
        ZALOPAY = 'ZALOPAY', _("ZaloPay")

    class PaymentStatus(models.TextChoices):
        IS_FAIL = "FAIL", _("Payment Fail")
        IS_SUCCESS = "SUCCESS", _("Payment Success")

    user = models.ForeignKey(User, related_name = "users", on_delete = models.PROTECT)
    order = models.ManyToManyField(Order, related_name = "orders")
    payment_method = models.CharField(max_length = 255, choices = PaymentMethod.choices, default = PaymentMethod.COD)
    payment_status = models.CharField(max_length = 255, choices = PaymentStatus.choices,
                                      default = PaymentStatus.IS_FAIL)
    total_amount = models.IntegerField(validators = [MinValueValidator(0)], null = False)


# -	Cửa hàng: Tên cửa hàng, người tạo cửa hàng(fk)
class Shop(BaseModel):
    name = models.CharField(max_length = 255, null = False)
    business = models.ForeignKey(Business, related_name = "business", on_delete = models.SET_NULL, null = True)
    email = models.EmailField(max_length = 255, default = None)
    phone = models.CharField(max_length = 10, null = False, default = "xs")
    address = models.CharField(max_length = 255, null = False, default = "xs")

    def __str__(self):
        return self.name


# -	Đánh giá sản phẩm: tiêu đề, nội dung, số sao, ngày đánh giá, sản phẩm, người đánh giá.
class ProductReview(BaseModel):
    user = models.ForeignKey(User, on_delete = models.SET_NULL, null = True, related_name = "product_reviews")
    product = models.ForeignKey(Product, on_delete = models.CASCADE, related_name = "product_reviews")
    rating = models.SmallIntegerField(default = 0)
    comment = models.TextField(blank = True, null = True)
    parent_comment = models.ForeignKey('self', null = True, blank = True, related_name = 'replies',
                                       on_delete = models.CASCADE)
    description = None


# -	Đánh giá cửa hàng: tiêu đề, nội dung, số sao, ngày đánh giá, sản phẩm, người đánh giá.
class ShopReview(BaseModel):
    user = models.ForeignKey(User, on_delete = models.SET_NULL, null = True)
    shop = models.ForeignKey(Shop, on_delete = models.CASCADE)
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank = True, null = True)
    parent_comment = models.ForeignKey('self', null = True, blank = True, related_name = 'replies',
                                       on_delete = models.CASCADE)
    description = None


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete = models.SET_NULL, null = True)


class CartDetail(models.Model):
    product = models.ForeignKey(Product, on_delete = models.CASCADE, null = True, related_name = "cart_detail")
    cart = models.ForeignKey(Cart, on_delete = models.CASCADE, null = True, related_name = "cart_detail")
    sizes = models.ForeignKey('size', blank = True, related_name = "cart_details", on_delete = models.CASCADE, default = 1)
    colors = models.ForeignKey("color", blank = True, related_name = "cart_details", on_delete = models.CASCADE, default = 1)
    quantity = models.IntegerField(validators = [MinValueValidator(0)], null = False, default = 0)

    def __str__(self):
        return self.product.name

    class Meta:
        unique_together = ('product', 'cart')
