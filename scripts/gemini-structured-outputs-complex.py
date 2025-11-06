import os
import json
from enum import Enum
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from google import genai

# ==========================================
# 1. Define Complex 30+ Field Pydantic Schema
# ==========================================

class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    UNKNOWN = "UNKNOWN"

class PaymentStatus(str, Enum):
    PAID = "PAID"
    PARTIAL = "PARTIAL"
    DUE = "DUE"

class InvoiceLineItem(BaseModel):
    description: str = Field(description="Raw description of the item or service row.")
    quantity: Optional[float] = Field(default=None, description="Numeric quantity, if found.")
    unit_code: Optional[str] = Field(default=None, description="Unit of measure (e.g., 'hours', 'each', 'lbs').")
    unit_price: Optional[float] = Field(default=None)
    discount_amount: Optional[float] = Field(default=None, description="Discount applied specifically to this line item.")
    line_total_amount: float = Field(description="Total for this line item after calculations.")

class SupplierDetails(BaseModel):
    name: str
    legal_address_line1: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None)
    postcode_zip: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None)
    vat_tax_id: Optional[str] = Field(default=None, description="VAT, GST, or Tax identification number.")
    support_email: Optional[str] = Field(default=None)
    support_phone: Optional[str] = Field(default=None)
    website_url: Optional[str] = Field(default=None)

class CustomerDetails(BaseModel):
    company_name: Optional[str] = Field(default=None)
    attention_to_name: Optional[str] = Field(default=None)
    billing_address: Optional[str] = Field(default=None)
    shipping_address: Optional[str] = Field(default=None)
    customer_tax_id: Optional[str] = Field(default=None)

class Invoice(BaseModel):
    # Header Details
    invoice_number: str = Field(description="Unique identifier for the invoice.")
    invoice_date: str = Field(description="Date the invoice was issued. ISO 8601 preferred if convertible, else raw string.")
    due_date: Optional[str] = Field(default=None, description="Payment due date.")
    purchase_order_number: Optional[str] = Field(default=None, description="Associated PO number if present.")
    
    # Parties
    supplier: SupplierDetails
    customer: CustomerDetails
    
    # Financial breakdown (Optional fields heavily used here for robustness)
    currency_code: Currency = Field(default=Currency.USD, description="Detected currency code.")
    subtotal_excluding_tax: Optional[float] = Field(default=None, description="Sum of items before tax.")
    total_tax_amount: Optional[float] = Field(default=None, description="Sum of all tax lines.")
    tax_percentage_rate: Optional[float] = Field(default=None, description="Primary tax rate (e.g., 0.20 for 20%).")
    total_shipping_fees: Optional[float] = Field(default=None)
    total_discount_amount: Optional[float] = Field(default=None, description="Total discount applied to the whole invoice.")
    grand_total_amount: float = Field(description="Final amount to be paid, inclusive of tax/shipping.")
    
    # Payment & Status Meta
    payment_terms_raw: Optional[str] = Field(default=None, description="Raw text terms like 'Net30' or 'Due upon receipt'.")
    payment_status_detected: PaymentStatus = Field(default=PaymentStatus.DUE)
    bank_account_number_detected: Optional[str] = Field(default=None, description="IBAN or account number for payment routing.")
    
    # Line items
    items: List[InvoiceLineItem] = Field(default_factory=list, description="Extract all visible line items rows.")

    # Metadata checks
    is_handwritten: bool = Field(default=False, description="Flag True if the document appears to be manually written.")
    has_ocr_errors: bool = Field(default=False, description="Flag True if text has evident scanning noise/garbled text.")


# ==========================================
# 2. Setup Client
# ==========================================
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# ==========================================
# 3. Realistic Complex Input (OCR Text)
# ==========================================
raw_ocr_text = """
[SCANNED DOCUMENT - OCR QUALITY: MEDIUM]
TECHSPHERE SOLUTIONS INC.
789 Innovation Drive,
Suite 200
Austin, TX 78701
Support: billing@techsphere-example.com | P: (512) 555-9876
VAT/TIN: US-889977665

INVOICE: TS-2024-0981
ISSUED: October 15th, 2024

Bill To:
Acme logistics co.
Attn: Sarah Jenkins
45 Warehouse Rd, Dock 4
Springfield, IL 62701
Tax ID: Unknown

PO Ref: PO_ACME_99283

DESCRIPTION                  QTY   UNIT    PRICE    DISC    TOTAL
-------------------------------------------------------------------
Pro-Tier Cloud Storage (TB)  50    TB      $20.00   10%     $900.00
Dedicated Support Hrs        10    Hrs     $150.00  -       $1500.00
Legacy System API Access     1     Ea      $450.00  -       $450.00
Q4 Server Maint Fee          1     Ea      $200.00  $50     $150.00

Subtotal: $3000.00
Sales Tax (TX 8.25%): $247.50
Shipping/Handling: $0.00
-----------------------------------
GRAND TOTAL: $3247.50 USD
Amount Paid: $0.00
Balance Due: $3247.50

Payment Terms: Net 30 days.
Pay via ACH to Routing: 123456789 Acct: 987654321
Note: Thank you for your continued business!
"""

# ==========================================
# 4. Realistic Detailed Prompt
# ==========================================
detailed_prompt = """
You are an expert invoice extraction agent. Your goal is to extract data from the provided invoice text with extremely high accuracy.

Follow these strict guidelines for extraction:
1. **Null Handling**: If a field exists in the schema but is NOT explicitly present in the document, you MUST return it as explicit `null` (None). Do not invent data.
2. **Dates**: Convert all dates to YYYY-MM-DD format if possible.
3. **Financials**: Normalize all currency values to floats (remove currency symbols like '$').
4. **Supplier Identification**: Look for the company issuing the invoice at the top.
5. **Customer Identification**: Look for the section labeled "Bill To", "Ship To", or "Client".
6. **Line Items**: Capture every single row in the table. Ensure unit quantities and rates are accurately split. Calculate line totals if the OCR is fuzzy.
7. **Taxation**: Extract both the total tax amount and the tax rate percentage if mentioned (e.g., "8.25%").
8. **Validation**: Ensure the 'subtotal' + 'tax' - 'discount' roughly equals the 'grand_total'.

Process the following incoming document text and map it to the requested JSON schema.
"""

# ==========================================
# 5. Execution with Gemini 2.5
# ==========================================
# Note: Gemini 2.5 Flash/Pro correctly interprets Pydantic `Optional` fields
# as `{"anyOf": [{"type": "..."}, {"type": "null"}]}`.
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[detailed_prompt, raw_ocr_text],
    config={
        "response_mime_type": "application/json",
        "response_json_schema": Invoice.model_json_schema(),
    },
)

# ==========================================
# 6. Output Parsing
# ==========================================
# Load directly into Pydantic model to validate structure
invoice_data = Invoice.model_validate_json(response.text)

# Print partial result verification
print(f"Extraction Status: Success")
print(f"Invoice No: {invoice_data.invoice_number}")
print(f"Supplier Tax ID: {invoice_data.supplier.vat_tax_id} (Optional field found)")
print(f"Customer Website: {invoice_data.supplier.website_url} (Optional field successfully null)")
print(f"Line Item count: {len(invoice_data.items)}")
print(f"Grand Total: {invoice_data.grand_total_amount} {invoice_data.currency_code.value}")

# Print full JSON
print("\nFull Parsed JSON output:\n")
print(invoice_data.model_dump_json(indent=2))