import uuid
from datetime import datetime

from pydantic import BaseModel


class DetectionEventResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    camera_id: uuid.UUID
    object_type: str
    count: int
    created_at: datetime

    model_config = {"from_attributes": True}
