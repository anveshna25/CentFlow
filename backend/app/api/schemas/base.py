from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema configuring standard model behavior."""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class ResponseEnvelope(BaseSchema, Generic[T]):
    """Standard success response envelope for a single payload."""

    data: T
    meta: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional metadata such as execution timing or provider source tags.",
    )


class PaginationMeta(BaseSchema):
    """Pagination metadata included in paginated list responses."""

    limit: int = Field(..., description="Maximum number of items returned.", ge=1)
    offset: int = Field(..., description="Number of items skipped.", ge=0)
    total: int = Field(..., description="Total number of items matching query.", ge=0)
    has_next: bool = Field(..., description="Whether additional items exist beyond this page.")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Standard success response envelope for paginated resource lists."""

    data: list[T]
    pagination: PaginationMeta


class ErrorDetail(BaseSchema):
    """Specific field or validation error detail."""

    field: Optional[str] = Field(default=None, description="Target field that caused error if applicable.")
    message: str = Field(..., description="Human-readable explanation of error.")
    type: Optional[str] = Field(default=None, description="Machine-readable error type identifier.")


class ErrorPayload(BaseSchema):
    """Standard error object payload."""

    code: str = Field(..., description="Machine-readable error code (e.g., NOT_FOUND, VALIDATION_ERROR).")
    message: str = Field(..., description="Human-readable summary of the error.")
    details: Optional[list[ErrorDetail]] = Field(default=None, description="Optional granular error details.")


class ErrorResponse(BaseSchema):
    """Standard top-level error response envelope."""

    error: ErrorPayload
