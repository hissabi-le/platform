from __future__ import annotations
import os, json, logging, math, re
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


def _coerce_float(x: Any) -> Optional[float]:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)): return None
        if isinstance(x, (int, float)): return float(x)
        s = str(x).strip().replace(",", "")
        m = re.search(r"(-?\d+(?:\.\d+)?)", s)
        return float(m.group(1)) if m else None
    except Exception:
        return None


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
        # 1) Responses API with JSON schema
        try:
            resp = self.client.responses.create(
                model=self.json_model,
                input=[{"role": "system", "content": system},
                       {"role": "user", "content": user}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "hissabi_schema", "schema": schema, "strict": True},
                },
                timeout=30,
            )
            text = resp.output_text
            data = json.loads(text)
            if isinstance(data, dict) and "items" in data:
                return data["items"] if isinstance(data["items"], list) else [data["items"]]
            if isinstance(data, list):
                return data
            return [data]
        except Exception as e:
            log.warning("OpenAI Responses API failed, trying chat.completions JSON: %s", e)

        # 2) Chat Completions with JSON object format (fallback)
        try:
            comp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                response_format={"type": "json_object"},
                timeout=30,
            )
            text = comp.choices[0].message.content or "{}"
            data = json.loads(text)
            if isinstance(data, dict) and "items" in data:
                return data["items"] if isinstance(data["items"], list) else [data["items"]]
            if isinstance(data, list):
                return data
            return [data]
        except Exception as e:
            log.error("OpenAI ChatCompletions fallback also failed: %s", e)
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
            return "Sorry—couldn’t run the assistant right now."
