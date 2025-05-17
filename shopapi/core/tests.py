from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from core.models import Product, WishList, Order, OrderProduct
import base64


def get_basic_auth_header(username, password):
    credentials = f"{username}:{password}".encode("utf-8")
    return {
        "HTTP_AUTHORIZATION": "Basic " + base64.b64encode(credentials).decode("utf-8")
    }


class APITests(TestCase):
    def setUp(self):
        self.client = Client()

        # Пользователь
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.admin = User.objects.create_user(username="admin", password="admin")

        # Группа менеджеры
        self.managers = Group.objects.create(name="менеджеры")
        self.managers.user_set.add(self.admin)

        # Продукт
        self.product = Product.objects.create(name="Тестовый товар", description="Описание", price=200)

        # Авторизация
        self.user_auth = get_basic_auth_header("testuser", "12345")
        self.admin_auth = get_basic_auth_header("admin", "admin")

    # ----- WISHLIST -----
    def test_wishlist_add_success(self):
        r = self.client.post("/api/wishlist/add", {"product_id": self.product.id, "count": 2}, content_type="application/json", **self.user_auth)
        self.assertEqual(r.status_code, 200)

    def test_wishlist_add_invalid_product(self):
        r = self.client.post("/api/wishlist/add", {"product_id": 9999, "count": 1}, content_type="application/json", **self.user_auth)
        self.assertEqual(r.status_code, 404)

    def test_wishlist_add_bad_structure(self):
        r = self.client.post("/api/wishlist/add", {"count": 1}, content_type="application/json", **self.user_auth)
        self.assertEqual(r.status_code, 422)

    # ----- ORDER -----
    def test_order_create_success(self):
        r = self.client.post("/api/order", {"product_id": self.product.id, "count": 1}, content_type="application/json", **self.user_auth)
        self.assertEqual(r.status_code, 200)

    def test_order_create_invalid_product(self):
        r = self.client.post("/api/order", {"product_id": 9999, "count": 1}, content_type="application/json", **self.user_auth)
        self.assertEqual(r.status_code, 404)

    def test_order_create_bad_structure(self):
        r = self.client.post("/api/order", {"count": 1}, content_type="application/json", **self.user_auth)
        self.assertEqual(r.status_code, 422)

    # ----- ORDER STATUS -----
    def test_order_update_status_success(self):
        order = Order.objects.create(user=self.user, total=200, status="новый")
        OrderProduct.objects.create(order=order, product=self.product, price=200, count=1)
        r = self.client.put(f"/api/order/{order.id}", {"status": "оплачен"}, content_type="application/json", **self.user_auth)
        self.assertEqual(r.status_code, 200)

    def test_order_update_status_wrong_id(self):
        r = self.client.put("/api/order/9999", {"status": "оплачен"}, content_type="application/json", **self.user_auth)
        self.assertEqual(r.status_code, 404)

    def test_order_update_status_structure_error(self):
        order = Order.objects.create(user=self.user, total=200, status="новый")
        r = self.client.put(f"/api/order/{order.id}", {}, content_type="application/json", **self.user_auth)
        self.assertEqual(r.status_code, 422)

    # ----- USERS (менеджеры) -----
    def test_users_list_success(self):
        r = self.client.get("/api/users", **self.admin_auth)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(len(r.json()) >= 1)

    def test_users_list_not_authorized(self):
        r = self.client.get("/api/users")
        self.assertEqual(r.status_code, 401)

    def test_users_list_not_manager(self):
        r = self.client.get("/api/users", **self.user_auth)
        self.assertEqual(r.status_code, 403)

    # ----- PRODUCT FILTER -----
    def test_product_filter_success(self):
        r = self.client.get("/api/products?min_price=100&max_price=300", **self.user_auth)
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()), 1)

    def test_product_filter_nothing_found(self):
        r = self.client.get("/api/products?min_price=100000", **self.user_auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 0)

    def test_product_filter_invalid_query(self):
        r = self.client.get("/api/products?min_price=abc", **self.user_auth)
        self.assertEqual(r.status_code, 422)
