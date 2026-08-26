from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import datetime


class AvailabilityCreateRequest(BaseModel):
    start_datetime: str
    end_datetime: str
    status: str = "AVAILABLE"
    note: Optional[str] = None

    @field_validator('start_datetime')
    @classmethod
    def validate_start(cls, v):
        if not v:
            raise ValueError('start_datetime est requis.')
        return v

    @field_validator('end_datetime')
    @classmethod
    def validate_end(cls, v):
        if not v:
            raise ValueError('end_datetime est requis.')
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed = ('AVAILABLE', 'UNAVAILABLE', 'RESERVED')
        if v not in allowed:
            raise ValueError(f'Statut invalide. Valeurs autorisées: {", ".join(allowed)}')
        return v

    @model_validator(mode='after')
    def validate_range(self):
        if self.start_datetime and self.end_datetime <= self.start_datetime:
            raise ValueError('end_datetime doit être supérieur à start_datetime.')
        return self


class AvailabilityUpdateRequest(BaseModel):
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ('AVAILABLE', 'UNAVAILABLE', 'RESERVED'):
            raise ValueError('Statut invalide. Valeurs autorisées: AVAILABLE, UNAVAILABLE, RESERVED')
        return v

    @model_validator(mode='after')
    def validate_range(self):
        if self.end_datetime is not None and self.start_datetime is not None:
            if self.end_datetime <= self.start_datetime:
                raise ValueError('end_datetime doit être supérieur à start_datetime.')
        return self


class AvailabilityResponse(BaseModel):
    id: str
    server_id: str
    start_datetime: str
    end_datetime: str
    status: str
    note: Optional[str] = None
    conflict: bool = False
    conflict_reason: Optional[str] = None


class AvailabilityCheckResponse(BaseModel):
    server_id: str
    event_id: str
    available: bool
    reason: Optional[str] = None


class ServerAvailabilityListResponse(BaseModel):
    server_id: str
    items: list[AvailabilityResponse]
