from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def error_payload(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_payload(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload("validation_error", _validation_message(exc.errors())),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "http_error"
        if exc.status_code == 401:
            code = "unauthorized"
        elif exc.status_code == 404:
            code = "not_found"
        elif exc.status_code == 405:
            code = "method_not_allowed"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code, str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )


def _validation_message(errors: list[dict[str, Any]]) -> str:
    if not errors:
        return "Invalid request"
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", []) if part != "body")
    message = first.get("msg", "Invalid request")
    return f"{location}: {message}" if location else message
