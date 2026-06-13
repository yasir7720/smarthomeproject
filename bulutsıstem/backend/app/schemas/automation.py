import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.automation import AutomationType


class ScheduleRequest(BaseModel):
    baslangic: str = Field(pattern=r"^\d{2}:\d{2}:\d{2}$", examples=["23:00:00"])
    bitis: str = Field(pattern=r"^\d{2}:\d{2}:\d{2}$", examples=["07:00:00"])


class AutomationRuleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    rule_type: AutomationType
    config_json: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ScenarioResponse(BaseModel):
    message: str
    tenant_id: uuid.UUID
