from django.contrib import admin
from .models import WishList, Order, OrderProduct, Product,ProductPhoto

admin.site.register(Product)
admin.site.register(WishList)
admin.site.register(Order)
admin.site.register(OrderProduct)
admin.site.register(ProductPhoto)