import pytest
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.main import app as main_app


def test_unhandled_exception_returns_safe_500():
    test_app = FastAPI()
    for exc_type, handler in main_app.exception_handlers.items():
        test_app.add_exception_handler(exc_type, handler)

    @test_app.get("/_test_unhandled")
    def _raise():
        raise RuntimeError("secret internal detail")

    client = TestClient(test_app, raise_server_exceptions=False)
    r = client.get("/_test_unhandled")
    assert r.status_code == 500
    assert "secret internal detail" not in r.text
    assert r.json()["detail"] == "Une erreur interne est survenue."


def test_http_exception_passthrough():
    test_app = FastAPI()
    for exc_type, handler in main_app.exception_handlers.items():
        test_app.add_exception_handler(exc_type, handler)

    @test_app.get("/_test_http_exc")
    def _http_exc():
        raise HTTPException(status_code=418, detail="teapot")

    client = TestClient(test_app, raise_server_exceptions=False)
    r = client.get("/_test_http_exc")
    assert r.status_code == 418
    assert r.json()["detail"] == "teapot"


def test_request_validation_error_preserves_structure():
    test_app = FastAPI()
    for exc_type, handler in main_app.exception_handlers.items():
        test_app.add_exception_handler(exc_type, handler)

    class Req(BaseModel):
        x: int

    @test_app.post("/_test_validation")
    async def _validation(payload: Req):
        return {"x": payload.x}

    client = TestClient(test_app, raise_server_exceptions=False)
    r = client.post("/_test_validation", json={"x": "not_int"})
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data
