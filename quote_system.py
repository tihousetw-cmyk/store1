#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional

TWOPLACES = Decimal("0.01")


@dataclass
class QuoteItem:
    name: str
    quantity: Decimal
    unit_price: Decimal
    discount_rate: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    taxable: bool = True

    def line_subtotal(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    def line_discount(self) -> Decimal:
        subtotal = self.line_subtotal()
        percentage_discount = (subtotal * self.discount_rate).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        total_discount = (percentage_discount + self.discount_amount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        if total_discount > subtotal:
            return subtotal
        return total_discount

    def line_total_before_tax(self) -> Decimal:
        return (self.line_subtotal() - self.line_discount()).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass
class QuoteData:
    quote_no: str
    quote_date: str
    customer_name: str
    company_name: str
    customer_phone: str
    customer_email: str
    customer_address: str
    tax_rate: Decimal
    items: List[QuoteItem]


def parse_decimal(value: str, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    normalized = re.sub(r"[^0-9.+-]", "", value)
    if normalized == "":
        return Decimal(default)
    return Decimal(normalized)


def parse_percentage(value: Optional[str], default: str = "0") -> Decimal:
    if not value:
        return Decimal(default)
    number = parse_decimal(value, default)
    if "%" in value or number > 1:
        return (number / Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return number.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def find_field(text: str, patterns: List[str], default: str = "") -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return default


def parse_items(text: str) -> List[QuoteItem]:
    items: List[QuoteItem] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # 主要格式：
    # 品項：網站維護；數量：2；單價：15000；折扣：10%；免稅：否
    structured_pattern = re.compile(
        r"^品項\s*[:：]\s*(?P<name>[^;；]+)"
        r"(?:[;；]\s*數量\s*[:：]\s*(?P<qty>[^;；]+))?"
        r"(?:[;；]\s*單價\s*[:：]\s*(?P<price>[^;；]+))?"
        r"(?:[;；]\s*折扣\s*[:：]\s*(?P<discount>[^;；]+))?"
        r"(?:[;；]\s*免稅\s*[:：]\s*(?P<nontax>[^;；]+))?"
        r"$"
    )

    # 備援格式：
    # 網站維護服務 x2 @15000
    fallback_pattern = re.compile(
        r"^(?P<name>.+?)\s*x\s*(?P<qty>[0-9.]+)\s*@\s*(?P<price>[0-9.,]+)$",
        flags=re.IGNORECASE,
    )

    for line in lines:
        sm = structured_pattern.match(line)
        if sm:
            discount_raw = sm.group("discount") or "0"
            discount_rate = Decimal("0")
            discount_amount = Decimal("0")
            if "%" in discount_raw:
                discount_rate = parse_percentage(discount_raw)
            else:
                # 允許小數折扣率，例如 0.15
                possible_rate = parse_decimal(discount_raw)
                if Decimal("0") < possible_rate < Decimal("1"):
                    discount_rate = possible_rate
                else:
                    discount_amount = possible_rate

            nontax = (sm.group("nontax") or "否").strip()
            taxable = nontax not in {"是", "yes", "y", "true", "1"}

            items.append(
                QuoteItem(
                    name=sm.group("name").strip(),
                    quantity=parse_decimal(sm.group("qty") or "1", "1"),
                    unit_price=parse_decimal(sm.group("price") or "0", "0"),
                    discount_rate=discount_rate,
                    discount_amount=discount_amount,
                    taxable=taxable,
                )
            )
            continue

        fm = fallback_pattern.match(line)
        if fm:
            items.append(
                QuoteItem(
                    name=fm.group("name").strip(),
                    quantity=parse_decimal(fm.group("qty"), "1"),
                    unit_price=parse_decimal(fm.group("price"), "0"),
                )
            )

    return items


def parse_quote_text(text: str) -> QuoteData:
    quote_no = find_field(text, [r"報價單號\s*[:：]\s*(.+)", r"quote\s*no\s*[:：]\s*(.+)"], "AUTO-QUOTE")
    quote_date = find_field(text, [r"日期\s*[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})"], str(date.today()))
    customer_name = find_field(text, [r"客戶名稱\s*[:：]\s*(.+)", r"姓名\s*[:：]\s*(.+)"], "未提供")
    company_name = find_field(text, [r"公司\s*[:：]\s*(.+)", r"公司名稱\s*[:：]\s*(.+)"], "未提供")
    customer_phone = find_field(text, [r"電話\s*[:：]\s*(.+)", r"手機\s*[:：]\s*(.+)"], "未提供")
    customer_email = find_field(text, [r"email\s*[:：]\s*(.+)", r"電子郵件\s*[:：]\s*(.+)"], "未提供")
    customer_address = find_field(text, [r"地址\s*[:：]\s*(.+)"], "未提供")
    tax_rate_raw = find_field(text, [r"稅率\s*[:：]\s*(.+)", r"tax\s*rate\s*[:：]\s*(.+)"], "5%")
    tax_rate = parse_percentage(tax_rate_raw, "0.05")

    items = parse_items(text)
    if not items:
        raise ValueError("找不到可辨識的品項資料，請確認包含『品項：...；數量：...；單價：...』格式。")

    return QuoteData(
        quote_no=quote_no,
        quote_date=quote_date,
        customer_name=customer_name,
        company_name=company_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        customer_address=customer_address,
        tax_rate=tax_rate,
        items=items,
    )


def money(value: Decimal) -> str:
    return f"{value.quantize(TWOPLACES, rounding=ROUND_HALF_UP):,.2f}"


def render_items_table(items: List[QuoteItem]) -> str:
    header = "| 品項 | 數量 | 單價 | 小計 | 折扣 | 稅前金額 | 課稅 |\n|---|---:|---:|---:|---:|---:|---|"
    rows = []
    for item in items:
        rows.append(
            "| {name} | {qty} | {unit} | {subtotal} | {discount} | {before_tax} | {taxable} |".format(
                name=item.name,
                qty=item.quantity.normalize(),
                unit=money(item.unit_price),
                subtotal=money(item.line_subtotal()),
                discount=money(item.line_discount()),
                before_tax=money(item.line_total_before_tax()),
                taxable="是" if item.taxable else "否",
            )
        )
    return "\n".join([header] + rows)


def calculate_totals(data: QuoteData) -> Dict[str, Decimal]:
    subtotal = sum((it.line_subtotal() for it in data.items), Decimal("0")).quantize(TWOPLACES)
    discount_total = sum((it.line_discount() for it in data.items), Decimal("0")).quantize(TWOPLACES)
    taxable_total = sum((it.line_total_before_tax() for it in data.items if it.taxable), Decimal("0")).quantize(TWOPLACES)
    non_taxable_total = sum((it.line_total_before_tax() for it in data.items if not it.taxable), Decimal("0")).quantize(TWOPLACES)
    tax_amount = (taxable_total * data.tax_rate).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    grand_total = (taxable_total + non_taxable_total + tax_amount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    return {
        "subtotal": subtotal,
        "discount_total": discount_total,
        "taxable_total": taxable_total,
        "non_taxable_total": non_taxable_total,
        "tax_amount": tax_amount,
        "grand_total": grand_total,
    }


def build_context(data: QuoteData) -> Dict[str, str]:
    totals = calculate_totals(data)
    return {
        "quote_no": data.quote_no,
        "quote_date": data.quote_date,
        "customer_name": data.customer_name,
        "company_name": data.company_name,
        "customer_phone": data.customer_phone,
        "customer_email": data.customer_email,
        "customer_address": data.customer_address,
        "tax_rate_percent": f"{(data.tax_rate * Decimal('100')).quantize(TWOPLACES)}%",
        "items_table": render_items_table(data.items),
        "subtotal": money(totals["subtotal"]),
        "discount_total": money(totals["discount_total"]),
        "taxable_total": money(totals["taxable_total"]),
        "tax_amount": money(totals["tax_amount"]),
        "grand_total": money(totals["grand_total"]),
    }


def apply_template(template: str, context: Dict[str, str]) -> str:
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="自動報價單系統：從文字抽取資料並產生報價單")
    parser.add_argument("--input", required=True, help="輸入文字檔路徑")
    parser.add_argument("--template", required=True, help="報價單模板檔案路徑（含 {{欄位}} 佔位符）")
    parser.add_argument("--output", required=True, help="輸出檔案路徑")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_text = Path(args.input).read_text(encoding="utf-8")
    template = Path(args.template).read_text(encoding="utf-8")

    data = parse_quote_text(input_text)
    context = build_context(data)
    output = apply_template(template, context)

    Path(args.output).write_text(output, encoding="utf-8")
    print(f"報價單已產生：{args.output}")


if __name__ == "__main__":
    main()
