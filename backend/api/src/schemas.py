from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict


class OrganisationBase(BaseModel):
    name: str


class OrganisationCreate(OrganisationBase):
    pass


class OrganisationRead(OrganisationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    email: str
    org_id: int
    role: str


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionBase(BaseModel):
    org_id: int
    stripe_subscription_id: Optional[str] = None
    plan: str
    status: str


class SubscriptionRead(SubscriptionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadBase(BaseModel):
    org_id: int
    filename: str
    status: str


class UploadCreate(UploadBase):
    pass


class UploadRead(UploadBase):
    id: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestionRunBase(BaseModel):
    upload_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_msg: Optional[str] = None


class IngestionRunRead(IngestionRunBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TransactionBase(BaseModel):
    org_id: int
    upload_id: int
    txn_date: datetime
    account_code: str
    category: str
    amount: float
    currency: str
    description: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionRead(TransactionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class DocumentRead(BaseModel):
    id:  int
    org_id:  int
    upload_id: Optional[int] = None
    doc_type:  str
    filename:  str
    content_type: str
    storage_path: str
    size_bytes:   int
    created_at:   datetime
    metadata_json: Optional[dict]

    class Config:
        orm_mode = True
