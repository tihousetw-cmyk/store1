import unittest
from decimal import Decimal

from quote_system import build_context, parse_quote_text


class QuoteSystemTest(unittest.TestCase):
    def test_parse_and_calculate(self):
        text = """
客戶名稱：王小明
公司：星辰科技股份有限公司
電話：0912-345-678
Email：xiaoming@example.com
地址：台北市信義區松仁路100號
報價單號：Q-20260409-001
日期：2026-04-09
稅率：5%

品項：網站維護服務；數量：2；單價：15000；折扣：10%
品項：雲端主機；數量：3；單價：4200；折扣：500
品項：資安稽核；數量：1；單價：30000；免稅：是
"""

        data = parse_quote_text(text)
        context = build_context(data)

        self.assertEqual(data.quote_no, "Q-20260409-001")
        self.assertEqual(data.tax_rate, Decimal("0.0500"))
        self.assertEqual(len(data.items), 3)

        # subtotal: 30000 + 12600 + 30000 = 72600
        self.assertEqual(context["subtotal"], "72,600.00")
        # discounts: 3000 + 500 + 0 = 3500
        self.assertEqual(context["discount_total"], "3,500.00")
        # taxable total: (30000-3000)+(12600-500)=39100
        self.assertEqual(context["taxable_total"], "39,100.00")
        # tax = 39100 * 5% = 1955
        self.assertEqual(context["tax_amount"], "1,955.00")
        # grand = taxable 39100 + nontax 30000 + tax 1955 = 71055
        self.assertEqual(context["grand_total"], "71,055.00")


if __name__ == "__main__":
    unittest.main()
