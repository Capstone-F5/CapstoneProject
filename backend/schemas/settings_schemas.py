from pydantic import BaseModel


class StartScreenImageOut(BaseModel):
    id: str
    image_url: str
    display_order: int

    model_config = {"from_attributes": True}
