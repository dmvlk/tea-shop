from pydantic import BaseModel, ConfigDict, Field

class CategoryBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=100)
    description: str | None = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    slug: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None

class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
