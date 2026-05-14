from dataclasses import dataclass, field


@dataclass
class InvoiceItem:
    name: str
    quantity: float
    unit: str
    price_per_unit: float
    total: float


@dataclass
class Invoice:
    items: list[InvoiceItem] = field(default_factory=list)
    raw_text: str = ""
