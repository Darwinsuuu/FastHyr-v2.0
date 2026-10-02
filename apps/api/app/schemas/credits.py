"""Workspace credit totals (BILLING.md §3)."""

from pydantic import BaseModel


class CreditSummary(BaseModel):
    """`balance` = credits not yet used or expired; `reserved` = held by pipelines' reserves;
    `free` = what a new reserve or top-up can still take."""

    balance: int
    reserved: int
    free: int
