# 自動報價單系統

這個專案提供一個可擴充的「文字轉報價單」工具：

1. 你只要給一段客戶與品項描述文字。
2. 系統會自動抽取對應欄位。
3. 套用到你提供的報價單格式模板（預設為 Markdown 範本）。
4. 自動進行較複雜金額運算（小計、折扣、稅額、總計）。

## 功能重點

- **欄位自動辨識**：客戶名稱、公司、電話、Email、地址、報價單號、日期、稅率等。
- **品項自動辨識**：品名、數量、單價、折扣（百分比或金額）、是否課稅。
- **計算邏輯**：
  - 品項小計 `數量 × 單價`
  - 折扣金額（百分比或固定金額）
  - 稅前金額
  - 稅金與含稅總價
- **可客製模板**：透過 `{{欄位名稱}}` 佔位符套用你的格式。

## 快速開始

```bash
python3 quote_system.py \
  --input sample_customer_text.txt \
  --template templates/quotation_template.md \
  --output output_quote.md
```

## 輸入文字格式（範例）

可混合自然語言與結構化提示，像這樣：

```text
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
```

## 模板佔位符

預設支援：

- `{{quote_no}}`
- `{{quote_date}}`
- `{{customer_name}}`
- `{{company_name}}`
- `{{customer_phone}}`
- `{{customer_email}}`
- `{{customer_address}}`
- `{{tax_rate_percent}}`
- `{{items_table}}`
- `{{subtotal}}`
- `{{discount_total}}`
- `{{taxable_total}}`
- `{{tax_amount}}`
- `{{grand_total}}`

如果你的模板有其他欄位，可在 `quote_system.py` 的 `build_context()` 擴充。

## 測試

```bash
python3 -m unittest -q
```

