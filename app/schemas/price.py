from pydantic import BaseModel


class PriceBase(BaseModel):
    ticker: str
    price: float
    timestamp: int


class PriceResponse(PriceBase):
    id: int

    class Config:
        from_attributes = True