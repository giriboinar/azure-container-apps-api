"""Pydantic models for the Task API."""

from pydantic import BaseModel, Field, field_validator


def _not_blank(value: str | None) -> str | None:
    """Strip whitespace; reject blank strings (None passes through for PATCH)."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError("title must not be blank")
    return stripped


class TaskCreate(BaseModel):
    """Payload for creating a task."""

    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        result = _not_blank(v)
        assert result is not None  # v is never None for a required field
        return result


class TaskUpdate(BaseModel):
    """Payload for partially updating a task. All fields optional."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    done: bool | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str | None) -> str | None:
        return _not_blank(v)


class Task(TaskCreate):
    """A task as stored and returned by the API."""

    id: str
    done: bool = False
