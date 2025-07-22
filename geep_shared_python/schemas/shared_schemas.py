from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings
from typing_extensions import Self


class UserType(Enum):
    REAL = "real"
    TEST = "test"
    SIM = "sim"


class DialogueType(Enum):
    REAL = "real"
    TEST = "test"
    SIM = "sim"


class A11yType(Enum):
    SUBTITLE = "subtitle"
    TRANSCRIPT = "transcript"


class SpeakerType(Enum):
    USER = "User"
    BOT = "The Bot"


class AsrType(Enum):
    ASSEMBLYAI = "assemblyai"
    DEEPGRAM = "deepgram"


class TaskStatusType(str, Enum):
    live = "live"
    test = "test"


class HealthCheck(BaseModel):
    """Response model to validate and return when performing a health check."""

    status: str = "OK"


class SharedSettings(BaseSettings):
    aws_region: str = ""
    db_user: str = ""
    db_password: str = ""
    db_host: str = ""
    db_name: str = ""
    db_port: str = ""
    environment: str = ""
    log_level: str = "info"
    log_use_colors: bool = True
    enable_metrics: bool = False
    dialogue_service_host: str = ""
    dialogue_service_port: int = 0
    llm_service_host: str = ""
    llm_service_port: int = 0
    task_service_host: str = ""
    task_service_port: int = 0
    prompt_service_host: str = ""
    prompt_service_port: int = 0


class UserTokenClaimsSchema(BaseModel):
    exp: datetime = Field(exclude=True)
    eol_id: int = Field(validation_alias="sub")
    country: str
    chatType: str = ""
    referringTheme: str = ""
    referringLesson: str = ""
    l2_language_level: str = Field(validation_alias="l2Proficiency")
    date_of_birth: date = Field(validation_alias="dob")
    redirectUrl: str = ""
    iss: str

    @model_validator(mode="after")
    def check_theme_or_lesson(self) -> Self:
        if not self.referringTheme and not self.referringLesson:
            raise ValueError(
                "Either referringTheme or referringLesson must be provided."
            )
        return self


class LlmV1StructuredChatResultSchema(BaseModel):
    """
    Defines the structured JSON object that the LLM is expected to generate
    as the content of its message when structured output mode is active.
    This schema is shared between the LLM service and its consumers.
    Version: 1
    """

    response: str = Field(
        ...,
        description="The textual response from the AI assistant intended for the end-user.",
    )

    end_conversation: bool = Field(
        ...,
        description="Boolean flag indicating if the conversation should end after this response.",
    )

    persona: Optional[Literal[1, 2]] = Field(
        default=None,
        description=(
            "Optional integer indicating the persona or bot ID that generated this "
            "response. Omit or set to null if not applicable, if only one persona is "
            "active, or if the LLM cannot determine a specific persona."
        ),
    )
