from pydantic import BaseModel, field_validator
from typing import Optional


class EvaluationCreateRequest(BaseModel):
    server_id: str
    punctuality: int
    work_quality: int
    presentation: int
    teamwork: int
    client_relation: int
    comment: Optional[str] = None

    @field_validator('punctuality', 'work_quality', 'presentation', 'teamwork', 'client_relation')
    @classmethod
    def validate_score(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Le score doit être compris entre 1 et 10.')
        return v


class EvaluationUpdateRequest(BaseModel):
    punctuality: Optional[int] = None
    work_quality: Optional[int] = None
    presentation: Optional[int] = None
    teamwork: Optional[int] = None
    client_relation: Optional[int] = None
    comment: Optional[str] = None

    @field_validator('punctuality', 'work_quality', 'presentation', 'teamwork', 'client_relation')
    @classmethod
    def validate_score(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError('Le score doit être compris entre 1 et 10.')
        return v


class EvaluationResponse(BaseModel):
    id: str
    event_id: str
    server_id: str
    server_name: str
    role: str
    punctuality: int
    work_quality: int
    presentation: int
    teamwork: int
    client_relation: int
    comment: Optional[str] = None
    created_at: str
