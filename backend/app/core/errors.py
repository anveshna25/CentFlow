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


class ProviderError(CentFlowException):
    """Base exception for market data provider errors."""

    def __init__(
        self,
        message: str,
        code: str = "PROVIDER_ERROR",
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        details: Optional[list[dict[str, Any]]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class ProviderUnavailableError(ProviderError):
    """Raised when an external market data provider is unreachable or unhealthy."""

    def __init__(self, provider_name: str, message: Optional[str] = None):
        super().__init__(
            message=message or f"Market data provider '{provider_name}' is currently unavailable.",
            code="PROVIDER_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=[{"provider": provider_name}],
        )


class ProviderTimeoutError(ProviderUnavailableError):
    """Raised when an external market data provider request times out."""

    def __init__(self, provider_name: str, message: Optional[str] = None):
        super().__init__(
            provider_name=provider_name,
            message=message or f"Request to market data provider '{provider_name}' timed out.",
        )
        self.code = "PROVIDER_TIMEOUT"
        self.status_code = status.HTTP_504_GATEWAY_TIMEOUT


class ProviderRateLimitError(ProviderError):
    """Raised when an external market data provider responds with rate limit / quota exceeded."""

    def __init__(self, provider_name: str, message: Optional[str] = None, retry_after: Optional[int] = None):
        details = [{"provider": provider_name}]
        if retry_after is not None:
            details[0]["retry_after"] = retry_after
        super().__init__(
            message=message or f"Rate limit exceeded for market data provider '{provider_name}'.",
            code="PROVIDER_RATE_LIMIT",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class ProviderResponseError(ProviderUnavailableError):
    """Raised when an external market data provider returns an invalid, empty, or malformed payload."""

    def __init__(self, provider_name: str, message: Optional[str] = None):
        super().__init__(
            provider_name=provider_name,
            message=message or f"Received an invalid or malformed response from provider '{provider_name}'.",
        )
        self.code = "PROVIDER_RESPONSE_ERROR"
        self.status_code = status.HTTP_502_BAD_GATEWAY


class ProviderAuthenticationError(ProviderError):
    """Raised when authentication or API credentials for a market data provider fail."""

    def __init__(self, provider_name: str, message: Optional[str] = None):
        super().__init__(
            message=message or f"Authentication failed for market data provider '{provider_name}'.",
            code="PROVIDER_AUTHENTICATION_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=[{"provider": provider_name}],
        )


class InstrumentNotFoundError(NotFoundError):
    """Raised when a specific financial instrument/symbol is not found by a provider or database."""

    def __init__(self, symbol: str):
        super().__init__(resource="Instrument", identifier=symbol)


class StaleDataError(CentFlowException):
    """Raised when market data exceeds the acceptable staleness threshold."""

    def __init__(self, symbol: str, staleness_seconds: int, threshold_seconds: int):
        super().__init__(
            message=f"Market quote for symbol '{symbol}' is stale ({staleness_seconds}s > {threshold_seconds}s threshold).",
            code="STALE_MARKET_DATA",
            status_code=status.HTTP_409_CONFLICT,
            details=[{
                "symbol": symbol,
                "staleness_seconds": staleness_seconds,
                "threshold_seconds": threshold_seconds,
            }],
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
