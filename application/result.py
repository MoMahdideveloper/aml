from dataclasses import dataclass
from typing import Generic, TypeVar, Optional

T = TypeVar('T')

@dataclass
class Success(Generic[T]):
    value: T

@dataclass
class RetryableError:
    message: str
    retry_after: Optional[int] = None

@dataclass
class PermanentError:
    message: str
    details: Optional[dict] = None

Result = Success[T] | RetryableError | PermanentError