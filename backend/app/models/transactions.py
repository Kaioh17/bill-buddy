from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base
import uuid

# The transactions stored exactly as plaid sends it
class Transaction(Base):
    __tablename__ = "transactions"
    transaction_id: mapped_column[str] = mapped_column(primary_key=True) # plaid's transaction_id 
    linked_account_id: mapped_column[uuid.UUID] = mapped_column(ForeignKey("linked_accounts.id", ondelete="CASCADE") , nullable=False) #forerign key-- not complete
    user_id: mapped_column[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plaid_account_id: mapped_column[str] = mapped_column() # plaid's account_id
    amount: mapped_column[float] = mapped_column()
    iso_currency_code: mapped_column[str] = mapped_column()
    date: mapped_column[datetime.date] = mapped_column()
    authorized_date: mapped_column[datetime.date] = mapped_column()
    pending: mapped_column[bool] = mapped_column()
    merchant_name: mapped_column[str] = mapped_column()
    merchant_entity_id: mapped_column[str] = mapped_column()
    original_description: mapped_column[str] = mapped_column()
    pfc_primary: mapped_column[str] = mapped_column() 
    pfc_detailed: mapped_column[str] = mapped_column()



