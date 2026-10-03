from pydantic import BaseModel, ConfigDict, Field


class AddressBase(BaseModel):
    city: str = Field(min_length=2, max_length=50)
    street: str = Field(min_length=2, max_length=50)
    building: str = Field(min_length=1, max_length=10)
    corpus: str | None = Field(default=None, max_length=10)
    apartment: str | None = Field(default=None, max_length=10)
    is_default: bool = False

class AddressCreate(AddressBase):
    pass

class AddressUpdate(BaseModel):
    city: str | None = Field(default=None, min_length=2, max_length=50)
    street: str | None = Field(default=None, min_length=2, max_length=50)
    building: str | None = Field(default=None, min_length=1, max_length=10)
    corpus: str | None = Field(default=None, max_length=10)
    apartment: str | None = Field(default=None, max_length=10)
    is_default: bool | None = None

class AddressRead(AddressBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
