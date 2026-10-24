from typing import Any, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class CentFlowException(Exception):
    """Base exception for all application-specific CentFlow errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[list[dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


class NotFoundError(CentFlowException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} '{identifier}' not found.",
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=[{"field": "id", "message": f"{resource} with identifier '{identifier}' was not found."}],
        )


class ValidationError(CentFlowException):
    """Raised when client input fails business or schema validation."""

    def __init__(self, message: str, details: Optional[list[dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class ConflictError(CentFlowException):
    """Raised when a resource state conflict occurs (e.g. duplicate key)."""

    def __init__(self, message: str, details: Optional[list[dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="CONFLICT_ERROR",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class BadRequestError(CentFlowException):
    """Raised when client sends malformed or invalid request data."""

    def __init__(self, message: str, details: Optional[list[dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="BAD_REQUEST",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


def _build_error_response(code: str, message: str, details: Optional[list[Any]] = None) -> dict[str, Any]:
    """Helper to build uniform error envelope."""
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        payload["error"]["details"] = details
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    """Register uniform exception handlers with the FastAPI application."""

    @app.exception_handler(CentFlowException)
    async def centflow_exception_handler(_: Request, exc: CentFlowException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        formatted_details = []
        for err in exc.errors():
            loc = ".".join(str(item) for item in err.get("loc", []) if item != "body")
            formatted_details.append(
                {
                    "field": loc or None,
                    "message": err.get("msg", "Validation error"),
                    "type": err.get("type", "value_error"),
                }
            )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_build_error_response(
                code="REQUEST_VALIDATION_ERROR",
                message="Request body or query parameters failed validation.",
                details=formatted_details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            500: "INTERNAL_SERVER_ERROR",
        }
        code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
        message = exc.detail if isinstance(exc.detail, str) else "HTTP exception occurred."
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_response(code=code, message=message),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_build_error_response(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred.",
            ),
        )
