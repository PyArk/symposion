from symposion.registration import models as rego

class ProductController(object):

    def __init__(self, product):
        self.product = product

    def user_can_add_within_limit(self, user, quantity):
        ''' Return true if the user is able to add _quantity_ to their count of
        this Product without exceeding _limit_per_user_.'''

        carts = rego.Cart.objects.filter(user=user)
        items = rego.ProductItem.objects.filter(product=self.product, cart=carts)

        count = 0
        for item in items:
            count += item.quantity

        if quantity + count > self.product.limit_per_user:
            return False
        else:
            return True

    def can_add_with_enabling_conditions(self, user, quantity):
        ''' Returns true if the user is able to add _quantity_ to their count
        of this Product without exceeding the ceilings the product is attached
        to. '''

        # TODO: capture ceilings based on category
        conditions = rego.EnablingConditionBase.objects.filter(
            products=self.product).select_subclasses()
        mandatory_violated = False
        non_mandatory_met = False

        for condition in conditions:
            cond = EnablingConditionController.for_condition(condition)
            met = cond.user_can_add(user, self.product, quantity)

            if condition.mandatory and not met:
                mandatory_violated = True
                break
            if met:
                non_mandatory_met = True

        if mandatory_violated:
            # All mandatory conditions must be met
            return False

        if len(conditions) > 0 and not non_mandatory_met:
            # If there's any non-mandatory conditions, one must be met
            return False

        return True


class EnablingConditionController(object):

    def __init__(self):
        pass

    @staticmethod
    def for_condition(condition):
        if isinstance(condition, rego.TimeOrStockLimitEnablingCondition):
            return TimeOrStockLimitEnablingConditionController(condition)
        else:
            return EnablingConditionController()

    def user_can_add(self, user, product, quantity):
        return True


class TimeOrStockLimitEnablingConditionController(EnablingConditionController):

    def __init__(self, ceiling):
        self.ceiling = ceiling

    def user_can_add(self, user, product, quantity):
        ''' returns True if adding _quantity_ of _product_ will not vioilate
        this ceiling. '''

        # TODO capture products based on categories
        if product not in self.ceiling.products.all():
            return True

        # TODO: test start_time
        # TODO: test end_time

        # Test limits
        count = 0
        product_items = rego.ProductItem.objects.filter(
            product=self.ceiling.products.all())
        for product_item in product_items:
            if True:
                # TODO: test that cart is paid or reserved
                count += product_item.quantity
        if count + quantity > self.ceiling.limit:
            return False

        # All limits have been met
        return True
