import datetime
import pytz

from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from symposion.registration import models as rego
from symposion.registration.cart import CartController

from test_cart import RegistrationCartTestCase

UTC = pytz.timezone('UTC')

class DiscountTestCase(RegistrationCartTestCase):

    @classmethod
    def add_discount_prod_1_includes_prod_2(cls, amount=Decimal(100)):
        discount = rego.IncludedProductDiscount.objects.create(
            description="PROD_1 includes PROD_2 " + str(amount) + "%",
        )
        discount.save()
        discount.enabling_products.add(cls.PROD_1)
        discount.save()
        rego.DiscountForProduct.objects.create(
            discount=discount,
            product=cls.PROD_2,
            percentage=amount,
            quantity=2
        ).save()
        return discount


    @classmethod
    def add_discount_prod_1_includes_cat_2(cls, amount=Decimal(100)):
        discount = rego.IncludedProductDiscount.objects.create(
            description="PROD_1 includes CAT_2 " + str(amount) + "%",
        )
        discount.save()
        discount.enabling_products.add(cls.PROD_1)
        discount.save()
        rego.DiscountForCategory.objects.create(
            discount=discount,
            category=cls.CAT_2,
            percentage=amount,
            quantity=2
        ).save()
        return discount


    def test_discount_is_applied(self):
        discount = self.add_discount_prod_1_includes_prod_2()

        cart = CartController.for_user(self.USER_1)
        cart.add_to_cart(self.PROD_1, 1)
        cart.add_to_cart(self.PROD_2, 1)

        # Discounts should be applied at this point...
        self.assertEqual(1, len(cart.cart.discountitem_set.all()))


    def test_discount_is_applied_for_category(self):
        discount = self.add_discount_prod_1_includes_cat_2()

        cart = CartController.for_user(self.USER_1)
        cart.add_to_cart(self.PROD_1, 1)
        cart.add_to_cart(self.PROD_3, 1)

        # Discounts should be applied at this point...
        self.assertEqual(1, len(cart.cart.discountitem_set.all()))


    def test_discount_does_not_apply_if_not_met(self):
        discount = self.add_discount_prod_1_includes_prod_2()

        cart = CartController.for_user(self.USER_1)
        cart.add_to_cart(self.PROD_2, 1)

        # No discount should be applied as the condition is not met
        self.assertEqual(0, len(cart.cart.discountitem_set.all()))


    def test_discounts_collapse(self):
        discount = self.add_discount_prod_1_includes_prod_2()

        cart = CartController.for_user(self.USER_1)
        cart.add_to_cart(self.PROD_1, 1)
        cart.add_to_cart(self.PROD_2, 1)
        cart.add_to_cart(self.PROD_2, 1)

        # Discounts should be applied and collapsed at this point...
        self.assertEqual(1, len(cart.cart.discountitem_set.all()))


    def test_discounts_respect_quantity(self):
        discount = self.add_discount_prod_1_includes_prod_2()

        cart = CartController.for_user(self.USER_1)
        cart.add_to_cart(self.PROD_1, 1)
        cart.add_to_cart(self.PROD_2, 3)

        # There should be three items in the cart, but only two should
        # attract a discount.
        discount_items = list(cart.cart.discountitem_set.all())
        self.assertEqual(2, discount_items[0].quantity)


    def test_multiple_discounts_apply_in_order(self):
        discount_full = self.add_discount_prod_1_includes_prod_2()
        discount_half = self.add_discount_prod_1_includes_prod_2(Decimal(50))

        cart = CartController.for_user(self.USER_1)
        cart.add_to_cart(self.PROD_1, 1)
        cart.add_to_cart(self.PROD_2, 3)

        # There should be two discounts
        discount_items = list(cart.cart.discountitem_set.all())
        discount_items.sort(key=lambda item: item.quantity)
        self.assertEqual(2, len(discount_items))
        # The half discount should be applied only once
        self.assertEqual(1, discount_items[0].quantity)
        self.assertEqual(discount_half.pk, discount_items[0].discount.pk)
        # The full discount should be applied twice
        self.assertEqual(2, discount_items[1].quantity)
        self.assertEqual(discount_full.pk, discount_items[1].discount.pk)


    def test_discount_applies_across_carts(self):
        discount_full = self.add_discount_prod_1_includes_prod_2()

        # Enable the discount during the first cart.
        cart = CartController.for_user(self.USER_1)
        cart.add_to_cart(self.PROD_1, 1)
        cart.cart.active = False
        cart.cart.save()

        # Use the discount in the second cart
        cart = CartController.for_user(self.USER_1)
        cart.add_to_cart(self.PROD_2, 1)

        # The discount should be applied.
        self.assertEqual(1, len(cart.cart.discountitem_set.all()))
        cart.cart.active = False
        cart.cart.save()

        # The discount should respect the total quantity across all
        # of the user's carts.
        cart = CartController.for_user(self.USER_1)
        cart.add_to_cart(self.PROD_2, 2)

        # Having one item in the second cart leaves one more item where
        # the discount is applicable. The discount should apply, but only for
        # quantity=1
        discount_items = list(cart.cart.discountitem_set.all())
        self.assertEqual(1, discount_items[0].quantity)


    def test_discount_applies_only_once_enabled(self):
        # Enable the discount during the first cart.
        cart = CartController.for_user(self.USER_1)
        cart.add_to_cart(self.PROD_1, 1)
        cart.add_to_cart(self.PROD_2, 2) # This would exhaust discount if present
        cart.cart.active = False
        cart.cart.save()

        discount_full = self.add_discount_prod_1_includes_prod_2()
        cart = CartController.for_user(self.USER_1)
        cart.add_to_cart(self.PROD_2, 2)

        discount_items = list(cart.cart.discountitem_set.all())
        self.assertEqual(2, discount_items[0].quantity)
