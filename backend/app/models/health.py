from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    project: str


class PingResponse(BaseModel):
    message: str
