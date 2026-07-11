from __future__ import annotations
from typing import Dict, List, Any
import pandas as pd
from app.data.repositories import get_business_repository, records_as_frame
from app.security.context import get_principal

def load_customers() -> pd.DataFrame:
    return records_as_frame("customers")

def load_tickets() -> pd.DataFrame:
    return records_as_frame("tickets")

def load_orders() -> pd.DataFrame:
    return records_as_frame("orders")

def load_crm_notes() -> pd.DataFrame:
    return records_as_frame("notes")

def get_customer_profile(customer_id: str) -> Dict[str, Any]:
    customers = load_customers()
    row = customers.loc[customers["customer_id"] == customer_id]
    if row.empty:
        return {"error": f"customer_id {customer_id} not found"}
    return row.iloc[0].to_dict()

def search_customers(query: str) -> List[Dict[str, Any]]:
    customers = load_customers()
    q = query.lower()
    mask = customers.apply(lambda r: q in " ".join(map(str, r.values)).lower(), axis=1)
    return customers.loc[mask].to_dict(orient="records")

def get_open_tickets(customer_id: str | None = None) -> List[Dict[str, Any]]:
    tickets = load_tickets()
    tickets = tickets.loc[tickets["status"].str.lower() != "closed"]
    if customer_id:
        tickets = tickets.loc[tickets["customer_id"] == customer_id]
    return tickets.to_dict(orient="records")

def get_overdue_orders(customer_id: str | None = None) -> List[Dict[str, Any]]:
    orders = load_orders()
    overdue = orders.loc[orders["payment_status"].str.lower() == "overdue"]
    if customer_id:
        overdue = overdue.loc[overdue["customer_id"] == customer_id]
    return overdue.to_dict(orient="records")

def get_recent_notes(customer_id: str | None = None, limit: int = 5) -> List[Dict[str, Any]]:
    notes = load_crm_notes()
    if customer_id:
        notes = notes.loc[notes["customer_id"] == customer_id]
    notes = notes.sort_values("date", ascending=False).head(limit)
    return notes.to_dict(orient="records")

def create_crm_task(
    customer_id: str,
    task: str,
    due_date: str,
    owner: str = "sales",
    idempotency_key: str | None = None,
) -> Dict[str, Any]:
    idempotency_key = idempotency_key or f"{customer_id}:{task}:{due_date}:{owner}"
    return get_business_repository().create_task(
        get_principal(),
        {
            "customer_id": customer_id,
            "task": task,
            "due_date": due_date,
            "owner": owner,
            "idempotency_key": idempotency_key,
        },
    )

def draft_followup_email(customer_name: str, reason: str, action: str) -> str:
    return (
        f"Hi {customer_name},\n\n"
        f"I wanted to follow up regarding {reason}. "
        f"Our team would like to {action} so we can resolve this properly.\n\n"
        f"Would you be available for a quick call this week?\n\n"
        f"Best regards,\nCustomer Success Team"
    )
