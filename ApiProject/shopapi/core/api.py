from ninja import NinjaAPI, Schema
from .models import Product, WishList, Order, OrderProduct
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from typing import List
from ninja.security import HttpBasicAuth
from ninja import Router
from ninja.errors import HttpError
from django.contrib.auth.models import Group
from .models import ProductPhoto

class GlobalAuth(HttpBasicAuth):
    def authenticate(self, request, username, password):
        from django.contrib.auth import authenticate
        user = authenticate(username=username, password=password)
        if user:
            return user

api = NinjaAPI(auth=GlobalAuth())

class UserOutSchema(Schema):
    id: int
    username: str
    email: str

class OrderCreateSchema(Schema):
    product_id: int
    count: int

class OrderOutSchema(Schema):
    id: int
    date: str
    status: str
    total: float

class WishListSchema(Schema):
    product_id: int
    count: int

class WishListOutSchema(Schema):
    id: int
    product_id: int
    count: int

class ProductFilterSchema(Schema):
    min_price: float = None
    max_price: float = None
    search_name: str = None
    search_description: str = None


from django.shortcuts import get_object_or_404
from ninja import Router

router = Router()


@router.get("/wishlist", response=List[WishListOutSchema])
def get_wishlist(request):
    wishlist = WishList.objects.filter(user=request.user)
    return [{"id": item.id, "product_id": item.product.id, "count": item.count} for item in wishlist]


@router.post("/wishlist/add")
def add_to_wishlist(request, data: WishListSchema):
    product = get_object_or_404(Product, id=data.product_id)
    wishlist_item, created = WishList.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={"count": data.count}
    )
    if not created:
        wishlist_item.count += data.count
        wishlist_item.save()
    return {"success": True}


@router.post("/wishlist/remove")
def remove_from_wishlist(request, data: WishListSchema):
    product = get_object_or_404(Product, id=data.product_id)
    WishList.objects.filter(user=request.user, product=product).delete()
    return {"success": True}


from datetime import datetime
from decimal import Decimal

@router.get("/order", response=List[OrderOutSchema])
def get_orders(request):
    orders = Order.objects.filter(user=request.user)
    return [
        {
            "id": order.id,
            "date": order.date.strftime("%Y-%m-%d %H:%M"),
            "status": order.status,
            "total": float(order.total)
        }
        for order in orders
    ]


@router.post("/order")
def create_order(request, data: OrderCreateSchema):
    product = get_object_or_404(Product, id=data.product_id)

    total_price = product.price * data.count

    order = Order.objects.create(
        user=request.user,
        status='новый',
        total=total_price
    )

    OrderProduct.objects.create(
        order=order,
        product=product,
        price=product.price,
        count=data.count
    )

    return {"order_id": order.id, "status": "created"}


class OrderStatusUpdateSchema(Schema):
    status: str  # ожидается: новый / оплачен / доставлен

@router.put("/order/{order_id}")
def update_order_status(request, order_id: int, data: OrderStatusUpdateSchema):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.status = data.status
    order.save()
    return {"status": "updated", "new_status": order.status}



def manager_required(request):
    if not request.user.is_authenticated:
        raise HttpError(401, "Вы не авторизованы")
    if not request.user.groups.filter(name__iexact="менеджеры").exists():
        raise HttpError(403, "Доступ запрещен: только для менеджеров")

from django.contrib.auth.models import User

@router.get("/users", response=List[UserOutSchema])
def get_users(request):
    manager_required(request)  # проверка доступа
    users = User.objects.all()
    return [{"id": u.id, "username": u.username, "email": u.email} for u in users]

from ninja import Query

@router.get("/products", response=List[dict])
def filter_products(request, filters: ProductFilterSchema = Query(...)):
    products = Product.objects.all()

    if filters.min_price is not None:
        products = products.filter(price__gte=filters.min_price)
    if filters.max_price is not None:
        products = products.filter(price__lte=filters.max_price)
    if filters.search_name:
        products = products.filter(name__icontains=filters.search_name)
    if filters.search_description:
        products = products.filter(description__icontains=filters.search_description)

    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": float(p.price)
        }
        for p in products
    ]

from ninja.files import UploadedFile
from django.core.files.storage import default_storage

@router.post("/products/{product_id}/upload_photo")
def upload_photo(request, product_id: int, file: UploadedFile):
    product = get_object_or_404(Product, id=product_id)

    photo = ProductPhoto.objects.create(
        product=product,
        image=file
    )

    return {"photo_id": photo.id, "url": photo.image.url}

@router.get("/products/{product_id}/photos", response=List[str])
def get_product_photos(request, product_id: int):
    product = get_object_or_404(Product, id=product_id)
    return [photo.image.url for photo in product.photos.all()]


api.add_router("/", router)

