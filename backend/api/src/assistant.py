from __future__ import annotations
import os, json, logging, math, re
from decimal import Decimal
from typing import Any, Iterable, Mapping, Optional

try:
    from openai import OpenAI
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False

log = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_JSON_MODEL = os.getenv("OPENAI_JSON_MODEL", DEFAULT_MODEL)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
CURRENCY_TOKENS = {"$", "usd", "eur", "€", "ll", "lbp", "ل.ل"}
REVENUE_TOKENS = {
    "sell",
    "sold",
    "sale",
    "revenu",
    "vente",
    "vendu",
    "بيع",
    "بعت",
    "حصل",
    "received",
    "cash-in",
}
COST_TOKENS = {
    "paid",
    "pay",
    "payé",
    "rent",
    "salary",
    "salaries",
    "wage",
    "electricity",
    "water",
    "internet",
    "utility",
    "tax",
    "parking",
    "fuel",
    "fees",
    "دفع",
    "ايجار",
    "فاتورة",
}
PURCHASE_TOKENS = {
    "buy",
    "bought",
    "purchase",
    "purchased",
    "acheté",
    "acheter",
    "اشترى",
    "شراء",
    "stocked",
}
USE_TOKENS = {
    "used",
    "use",
    "consumed",
    "consommé",
    "utilisé",
    "utiliser",
    "استعمل",
    "استهلك",
}
TRANSFER_TOKENS = {
    "transfer",
    "transferred",
    "حول",
    "حوّل",
    "virement",
}
INGREDIENT_KEYWORDS = {
    "milk",
    "sugar",
    "flour",
    "butter",
    "coffee",
    "beans",
    "tea",
    "bread",
    "egg",
    "chicken",
    "meat",
    "rice",
    "spice",
    "packaging",
    "cups",
    "bags",
    "boxes",
    "مواد",
    "مكونات",
    "lait",
    "farine",
    "beurre",
}
FIXED_EXPENSES = {
    "rent",
    "electricity",
    "water",
    "internet",
    "salary",
    "wage",
    "transport",
    "fuel",
    "maintenance",
    "marketing",
    "tax",
    "marketing",
    "maintenance",
    "utilité",
    "loyer",
}
UNIT_ALIASES = {
    "kg": "kg",
    "kilo": "kg",
    "kilogram": "kg",
    "kilogramme": "kg",
    "g": "g",
    "gram": "g",
    "grams": "g",
    "l": "l",
    "liter": "l",
    "litre": "l",
    "piece": "piece",
    "pieces": "piece",
    "pcs": "piece",
    "dozen": "dozen",
    "dz": "dozen",
    "unit": "unit",
    "units": "unit",
}

def _coerce_float(x: Any) -> Optional[float]:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)): return None
        if isinstance(x, (int, float)): return float(x)
        s = str(x).strip().replace(",", "")
        m = re.search(r"(-?\d+(?:\.\d+)?)", s)
        return float(m.group(1)) if m else None
    except Exception:
        return None


def _normalize_language_token(line: str) -> str:
    return line.translate(ARABIC_DIGITS).lower()


def _detect_language(lines: list[str]) -> str:
    for line in lines:
        if re.search(r"[\u0600-\u06FF]", line):
            return "ar"
    for line in lines:
        lower = line.lower()
        if any(word in lower for word in ("bonjour", "merci", "acheté", "vente", "euro")):
            return "fr"
    return "en"


def _normalize_amount_fragment(fragment: str) -> str:
    cleaned = fragment.translate(ARABIC_DIGITS)
    cleaned = cleaned.replace("٬", "").replace(",", "").replace(" ", "")
    return cleaned


def _extract_quantity(line: str) -> tuple[Optional[Decimal], Optional[str], Optional[tuple[int, int]]]:
    pattern = re.compile(
        r"(?P<qty>-?\d+(?:[\,\.]\d+)?)\s*(?P<unit>kg|kilograms?|kilo|g|grams?|l|liters?|litres?|piece|pieces|pcs|dozen|dz|unit|units)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(line):
        qty_raw = _normalize_amount_fragment(match.group("qty"))
        try:
            qty = Decimal(qty_raw)
        except Exception:
            continue
        unit_key = match.group("unit").lower()
        unit = UNIT_ALIASES.get(unit_key, unit_key)
        return qty, unit, match.span()
    return None, None, None


def _extract_amount(line: str, skip_span: Optional[tuple[int, int]]) -> Optional[Decimal]:
    candidates: list[tuple[Decimal, int]] = []
    for match in re.finditer(r"(-?\d+(?:[\,\.]\d+)?)", line):
        span = match.span()
        if skip_span and span[0] >= skip_span[0] and span[1] <= skip_span[1]:
            continue
        raw = _normalize_amount_fragment(match.group(0))
        try:
            amount = Decimal(raw)
        except Exception:
            continue
        candidates.append((amount, span[0]))
    if not candidates:
        return None
    # prefer numbers that are near currency hints
    best_amount = candidates[-1][0]
    best_score = -1
    for amount, pos in candidates:
        window = line[max(0, pos - 8): pos + 8].lower()
        score = 0
        if any(token in window for token in CURRENCY_TOKENS):
            score += 2
        if pos > (skip_span[1] if skip_span else -1):
            score += 1
        if score > best_score:
            best_score = score
            best_amount = amount
    return best_amount


def _detect_vat(line: str) -> tuple[Optional[Decimal], Optional[bool]]:
    lower = line.lower()
    if not any(tag in lower for tag in ("vat", "tva", "ضريبة")):
        return None, None
    match = re.search(r"(\d{1,2}(?:[\,\.]\d+)?)\s*%", lower)
    if match:
        raw = _normalize_amount_fragment(match.group(1))
        try:
            return Decimal(raw), None
        except Exception:
            pass
    return None, True


def _tokens(line: str) -> list[str]:
    norm = _normalize_language_token(line)
    return re.findall(r"[a-z\u0600-\u06FF]+", norm)


def _guess_entry_type(tokens: list[str]) -> str:
    if any(tok in tokens for tok in TRANSFER_TOKENS):
        return "transfer"
    if any(tok in tokens for tok in REVENUE_TOKENS):
        return "revenue"
    if any(tok in tokens for tok in USE_TOKENS):
        return "inventory_use"
    if any(tok in tokens for tok in PURCHASE_TOKENS):
        return "inventory_purchase"
    if any(tok in tokens for tok in COST_TOKENS):
        return "cost"
    return "cost"


def _infer_category(entry_type: str, item_name: Optional[str], tokens: list[str]) -> Optional[str]:
    lowered_item = (item_name or "").lower()
    relevant = tokens + lowered_item.split()
    if entry_type == "revenue":
        return "Sales"
    if entry_type == "inventory_purchase":
        if any(tok in INGREDIENT_KEYWORDS for tok in relevant):
            return "Ingredients"
        return None
    if entry_type == "inventory_use":
        return "Ingredients"
    if any(tok in FIXED_EXPENSES for tok in relevant):
        return "Fixed Expense"
    return None


def _normalize_entry_payload(entry: dict[str, Any]) -> dict[str, Any]:
    # Map 'amount' to 'total' since LLM sometimes returns 'amount' instead of 'total'
    total_value = entry.get("total") or entry.get("amount")
    
    normalised = {
        "entry_type": entry.get("entry_type"),
        "item_name": entry.get("item_name"),
        "quantity": None,
        "unit": entry.get("unit"),
        "unit_cost": None,
        "total": None,
        "category": entry.get("category"),
        "vat_percent": None,
        "vat_included": entry.get("vat_included"),
        "notes": entry.get("notes"),
        "ambiguous": bool(entry.get("ambiguous", False)),
        "clarification_question": entry.get("clarification_question"),
        "resolved": entry.get("resolved", True),
    }
    
    # Process numeric fields
    for key in ("quantity", "unit_cost", "vat_percent"):
        value = entry.get(key)
        if value is None:
            continue
        try:
            normalised[key] = Decimal(str(value))
        except Exception:
            normalised[key] = None
            normalised["ambiguous"] = True
            if not normalised["clarification_question"]:
                normalised["clarification_question"] = f"unable to parse numeric value for {key}"
    
    # Handle total/amount separately - extract number from strings like "25$", "$25", "25.00$"
    if total_value is not None:
        try:
            # Try direct conversion first
            normalised["total"] = Decimal(str(total_value))
        except Exception:
            # Extract numeric portion from strings like "25$" or "$25.00"
            str_val = str(total_value)
            match = re.search(r"(-?\d+(?:[,\.]\d+)?)", str_val.replace(",", ""))
            if match:
                try:
                    normalised["total"] = Decimal(match.group(1))
                except Exception:
                    normalised["total"] = None
                    normalised["ambiguous"] = True
                    if not normalised["clarification_question"]:
                        normalised["clarification_question"] = "unable to parse total amount"
            else:
                normalised["total"] = None
                normalised["ambiguous"] = True
                if not normalised["clarification_question"]:
                    normalised["clarification_question"] = "unable to parse total amount"
    
    return normalised


def _heuristic_parse(lines: list[str], language: str) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        tokens = _tokens(stripped)
        entry_type = _guess_entry_type(tokens)
        qty, unit, qty_span = _extract_quantity(stripped)
        amount = _extract_amount(stripped, qty_span)
        vat_percent, vat_included = _detect_vat(stripped)

        item_name = stripped
        if tokens:
            # keep phrases excluding verbs for readability
            item_tokens = [tok for tok in tokens if tok not in REVENUE_TOKENS | COST_TOKENS | PURCHASE_TOKENS | USE_TOKENS | TRANSFER_TOKENS]
            if item_tokens:
                item_name = " ".join(item_tokens)

        entry = {
            "entry_type": entry_type,
            "item_name": item_name.strip()[:255],
            "quantity": qty,
            "unit": unit,
            "unit_cost": None,
            "total": amount,
            "category": _infer_category(entry_type, item_name, tokens),
            "vat_percent": vat_percent,
            "vat_included": vat_included,
            "notes": None,
            "ambiguous": False,
            "clarification_question": None,
            "resolved": True,
        }

        if entry_type in {"inventory_purchase", "inventory_use"} and qty is None:
            entry["ambiguous"] = True
            entry["clarification_question"] = "please provide quantity for inventory movement"
            entry["resolved"] = False
        if amount is None and entry_type in {"revenue", "cost"}:
            entry["ambiguous"] = True
            entry["clarification_question"] = "please confirm the total amount for this line"
            entry["resolved"] = False
        if entry_type == "inventory_purchase" and entry["category"] is None:
            entry["ambiguous"] = True
            entry["clarification_question"] = "should this purchase be tracked as inventory or expensed today?"
            entry["resolved"] = False

        entries.append(_normalize_entry_payload(entry))

    return {"entries": entries, "language": language}


class OpenAIClient:
    """Centralized LLM adapter used across inventory + accounting."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, json_model: Optional[str] = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or DEFAULT_MODEL
        self.json_model = json_model or DEFAULT_JSON_MODEL
        if _HAS_OPENAI and self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None  # triggers fallback paths

    # ------------------- internal helpers -------------------

    def _responses_json(self, system: str, user: str, schema: dict) -> list[dict[str, Any]]:
        """
        Call OpenAI Responses API with a strict JSON schema.
        Fallback to Chat Completions JSON object if Responses fails.
        Final fallback: return [].
        """
        if not self.client:
            return []
        
        # Use Chat Completions with JSON object format
        try:
            comp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                response_format={"type": "json_object"},
                timeout=30,
            )
            text = comp.choices[0].message.content or "{}"
            log.info(f"OpenAI raw response: {text}")
            data = json.loads(text)
            if isinstance(data, dict) and "items" in data:
                return data["items"] if isinstance(data["items"], list) else [data["items"]]
            if isinstance(data, list):
                return data
            # If the schema expected a root object with "entries" (for journal), return that wrapper or list
            # The calling function (parse_journal_lines) expects a dict with "entries" or a list.
            return [data]
        except Exception as e:
            log.error("OpenAI ChatCompletions failed: %s", e)
            return []

    # ------------------- inventory mapping -------------------

    def map_rows_to_inventory(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Normalize messy tabular rows into structured inventory lines:
        { Item:str, Qty:float|null, Unit:str|null, Amount:float|null, SKU:str|null }
        """
        system = (
            "You are a strict accounting inventory normalizer. "
            "Given messy rows from an uploaded sheet, return only real physical stock items. "
            "Each item must include: Item (name), optional Qty (number), Unit (e.g., kg, dozen, piece), "
            "optional Amount (total monetary amount for that line), and optional SKU."
        )
        user = json.dumps({"rows": rows}, ensure_ascii=False)
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Item":   {"type": "string"},
                            "Qty":    {"type": ["number", "null"]},
                            "Unit":   {"type": ["string", "null"]},
                            "Amount": {"type": ["number", "null"]},
                            "SKU":    {"type": ["string", "null"]},
                        },
                        "required": ["Item"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["items"],
            "additionalProperties": False,
        }
        out = self._responses_json(system, user, schema)
        if out:  # successful model return
            return out

        # --- deterministic fallback (no API key / offline) ---
        mapped: list[dict[str, Any]] = []
        for r in rows:
            item = r.get("Item") or r.get("Description") or r.get("Account") or r.get("Product") or r.get("Name")
            if not item:  # skip rows with no obvious item descriptor
                continue
            mapped.append({
                "Item": str(item).strip(),
                "Qty": _coerce_float(r.get("Qty") or r.get("Quantity") or r.get("QTY")),
                "Unit": (r.get("Unit") or r.get("UOM") or r.get("Units") or None),
                "Amount": _coerce_float(r.get("Amount") or r.get("Total") or r.get("Price") or r.get("Cost")),
                "SKU": (r.get("SKU") or r.get("Code") or None),
            })
        return mapped

    # ------------------- account classification -------------------

    def classify_accounts(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Map free-text account names into buckets: assets, liabilities, equity, revenue, cogs, expense.
        """
        system = (
            "Classify each 'account' into one of: assets, liabilities, equity, revenue, cogs, expense. "
            "Be conservative for ambiguous names."
        )
        user = json.dumps({"rows": rows}, ensure_ascii=False)
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "account": {"type": "string"},
                            "bucket":  {"type": "string"},
                        },
                        "required": ["account", "bucket"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["items"],
            "additionalProperties": False,
        }
        out = self._responses_json(system, user, schema)
        if out:
            return out

        # fallback heuristics
        def guess(a: str) -> str:
            al = a.lower()
            if any(w in al for w in ["cash", "bank", "receivable", "inventory", "asset", "prepaid"]): return "assets"
            if any(w in al for w in ["payable", "loan", "debt", "accrued", "tax payable"]): return "liabilities"
            if any(w in al for w in ["equity", "capital", "retained", "earnings", "dividend"]): return "equity"
            if any(w in al for w in ["revenue", "sales", "income"]): return "revenue"
            if any(w in al for w in ["cogs", "cost of goods"]): return "cogs"
            return "expense"
        return [{"account": r.get("account", ""), "bucket": guess(r.get("account", ""))} for r in rows if r.get("account")]

    # ------------------- financial document generation -------------------

    def parse_journal_lines(self, lines: Iterable[str], locale: Optional[str] = None) -> dict[str, Any]:
        entries_list = [line.strip() for line in lines if line and line.strip()]
        detected_language = locale or _detect_language(entries_list)
        if not entries_list:
            return {"entries": [], "language": detected_language}

        system_prompt = (
            "you convert short daily accounting notes into strict json.\n"
            "understand english, french, and arabic (including arabizi).\n"
            "allowed entry_type values: revenue, cost, inventory_purchase, inventory_use, transfer.\n"
            "copy monetary totals exactly as written (do not calculate new totals).\n"
            "if uncertain, set ambiguous=true, resolved=false, and include a short clarification_question.\n"
            "provide quantity/unit when explicitly mentioned.\n"
            "use common categories like Sales, Ingredients, Fixed Expense, Utilities, Wages, Rent when clear, else null.\n"
            "detect vat or tva mentions and capture vat_percent when numeric.\n"
            "output strictly in this schema without comments."
        )

        journal_schema = {
            "type": "object",
            "properties": {
                "language": {"type": "string"},
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "entry_type": {"type": "string"},
                            "item_name": {"type": ["string", "null"]},
                            "quantity": {"type": ["number", "null"]},
                            "unit": {"type": ["string", "null"]},
                            "unit_cost": {"type": ["number", "null"]},
                            "total": {"type": ["number", "null"]},
                            "category": {"type": ["string", "null"]},
                            "vat_percent": {"type": ["number", "null"]},
                            "vat_included": {"type": ["boolean", "null"]},
                            "notes": {"type": ["string", "null"]},
                            "ambiguous": {"type": "boolean"},
                            "clarification_question": {"type": ["string", "null"]},
                            "resolved": {"type": "boolean"},
                        },
                        "required": ["entry_type", "total", "ambiguous", "resolved"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["entries"],
            "additionalProperties": False,
        }

        allowed_types = {
            "revenue",
            "cost",
            "inventory_purchase",
            "inventory_use",
            "transfer",
        }

        if self.client:
            user_payload = json.dumps(
                {
                    "lines": entries_list,
                    "locale": detected_language,
                },
                ensure_ascii=False,
            )
            llm_entries = self._responses_json(system_prompt, user_payload, journal_schema)
            if llm_entries:
                raw_entries = llm_entries[0].get("entries") if isinstance(llm_entries[0], dict) else llm_entries
                final_entries: list[dict[str, Any]] = []
                for raw in raw_entries or []:
                    entry = dict(raw)
                    entry_type = entry.get("entry_type")
                    if entry_type not in allowed_types:
                        entry["entry_type"] = "cost"
                        entry["ambiguous"] = True
                        entry["resolved"] = False
                        entry["clarification_question"] = (
                            entry.get("clarification_question")
                            or "unable to map entry type, please review this line"
                        )
                    normalised = _normalize_entry_payload(entry)
                    final_entries.append(normalised)
                
                # Check if we actually got entries; if not, fallback to heuristic
                if final_entries:
                    language_value = llm_entries[0].get("language") if isinstance(llm_entries[0], dict) else detected_language
                    return {
                        "entries": final_entries,
                        "language": language_value or detected_language,
                    }
                else:
                    log.warning("OpenAI returned no entries, falling back to heuristic")

        return _heuristic_parse(entries_list, detected_language)

    def generate_documents(self, context: dict, request: dict) -> dict:
        """
        Given normalized context (e.g., rolled-up windows) and a request specifying which documents
        to produce, return JSON with keys drawn from:
        balance_sheet, pnl, roi, cost_breakdown, cost_breakdown_pct, unit_cost_pct, sales_projection, scenarios
        """
        system = (
            "You are Hissabi's accounting assistant. "
            "Using the provided context (already aggregated numbers and summaries), emit ONLY JSON. "
            "Keys allowed: balance_sheet, pnl, roi, cost_breakdown, cost_breakdown_pct, unit_cost_pct, sales_projection, scenarios. "
            "Do not invent unknown numbers; leave nulls if insufficient data. Be conservative and consistent."
        )
        user = json.dumps({"context": context, "request": request}, ensure_ascii=False)
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "object",
                    "properties": {
                        "balance_sheet":       {"type": ["object", "null"]},
                        "pnl":                 {"type": ["object", "null"]},
                        "roi":                 {"type": ["object", "null"]},
                        "cost_breakdown":      {"type": ["object", "null"]},
                        "cost_breakdown_pct":  {"type": ["object", "null"]},
                        "unit_cost_pct":       {"type": ["object", "null"]},
                        "sales_projection":    {"type": ["object", "null"]},
                        "scenarios":           {"type": ["object", "null"]},
                    },
                    "additionalProperties": False,
                }
            },
            "required": ["items"],
            "additionalProperties": False,
        }
        out = self._responses_json(system, user, schema)
        if out and isinstance(out[0], dict):
            return out[0]

        # fallback: return empty dict; deterministic pieces should already be in `context`
        return {}

    # ------------------- Q&A over a balance sheet -------------------

    def chat(self, prompt: str) -> str:
        """
        Plain-text chat completion. Used by the personal finance chat endpoint.
        Falls back to a polite offline message if no API key is configured.
        """
        if not self.client:
            return (
                "I'm currently running in offline mode and can't provide AI-powered responses. "
                "Please ensure an OpenAI API key is configured to enable the chat feature."
            )

        messages = [
            {"role": "user", "content": prompt},
        ]
        try:
            comp = self.client.chat.completions.create(
                model=self.model, messages=messages, timeout=30
            )
            return (comp.choices[0].message.content or "").strip()
        except Exception as e:
            log.error("chat failed: %s", e)
            return "Sorry — I couldn't process your request right now. Please try again."

    def answer_question(self, balance_data: dict, question: str) -> str:
        """
        Freeform Q&A about computed balance data. Falls back to a simple template if no API.
        """
        if not self.client:
            # minimal offline behavior
            total_assets = balance_data.get("totals", {}).get("assets") or balance_data.get("Assets", {}).get("Total Assets")
            total_liab = balance_data.get("totals", {}).get("liabilities") or balance_data.get("Liabilities", {}).get("Total Liabilities")
            total_eq = balance_data.get("totals", {}).get("equity") or balance_data.get("Equity", {}).get("Total Equity")
            return f"(LLM offline) Assets={total_assets}, Liabilities={total_liab}, Equity={total_eq}. Question: {question}"

        messages = [
            {"role": "system", "content": "You are a concise financial assistant. Keep answers short, factual, and use numbers from the provided JSON only."},
            {"role": "user", "content": f"Balance data (JSON):\n```json\n{json.dumps(balance_data, ensure_ascii=False)}\n```\n\nQuestion: {question}"},
        ]
        try:
            comp = self.client.chat.completions.create(model=self.model, messages=messages, timeout=30)
            return (comp.choices[0].message.content or "").strip()
        except Exception as e:
            log.error("answer_question failed: %s", e)
            return "Sorry—couldn't run the assistant right now."
