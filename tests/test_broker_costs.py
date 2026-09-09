import unittest

from broker_costs import (
    AlpacaPersonalApiCostModel,
    CustomFlatCostModel,
    get_broker_cost_model,
    round_up_cent,
)


class BrokerCostTests(unittest.TestCase):
    def test_alpaca_buy_has_no_fees(self):
        fees = AlpacaPersonalApiCostModel().calculate(
            side="buy", quantity=5, price=200.0
        )

        self.assertEqual(fees.total, 0.0)

    def test_alpaca_sell_applies_sec_and_finra_fees(self):
        fees = AlpacaPersonalApiCostModel().calculate(
            side="sell", quantity=5, price=200.0
        )

        self.assertEqual(fees.broker_commission, 0.0)
        self.assertEqual(fees.sec_fee, 0.03)
        self.assertEqual(fees.finra_taf, 0.01)
        self.assertEqual(fees.total, 0.04)

    def test_finra_taf_is_capped(self):
        fees = AlpacaPersonalApiCostModel().calculate(
            side="sell", quantity=100_000, price=1.0
        )

        self.assertEqual(fees.finra_taf, 9.79)

    def test_custom_profile_charges_each_order(self):
        model = CustomFlatCostModel(commission_per_order=1.25)

        self.assertEqual(model.calculate(side="buy", quantity=1, price=100).total, 1.25)
        self.assertEqual(model.calculate(side="sell", quantity=1, price=100).total, 1.25)

    def test_profile_factory_rejects_unknown_broker(self):
        with self.assertRaisesRegex(ValueError, "unknown broker"):
            get_broker_cost_model("missing")

    def test_rounding_is_conservative_to_the_cent(self):
        self.assertEqual(round_up_cent(0.0001), 0.01)
        self.assertEqual(round_up_cent(0.01), 0.01)
