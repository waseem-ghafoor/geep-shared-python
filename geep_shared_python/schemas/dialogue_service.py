import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from geep_shared_python.schemas.shared_schemas import (
    A11yType,
    AsrType,
    SpeakerType,
    DialogueType,
)

########################
# API Request Schemas  #
########################


class BaseA11yRequestSchema(BaseModel):
    pass


class A11yRequestSchema(BaseA11yRequestSchema):
    """
    used by DialogueV2RequestSchema
    """

    asset: str
    type: A11yType
    start: float
    end: Optional[float] = None

    model_config = ConfigDict(use_enum_values=True)


class BaseDialogueRequestSchema(BaseModel):
    pass


class DialogueRequestSchema(BaseDialogueRequestSchema):
    pass


class DialogueV2RequestSchema(DialogueRequestSchema):
    """
    /dialogue
    """

    task_id: str
    task_version: int
    l2_language_level: Optional[str]
    l1_language: Optional[str]
    dialogue_type: Optional[str] = DialogueType.REAL.value
    a11y_events: Optional[list[A11yRequestSchema]] = None


class DialogueSurveyRequestSchema(DialogueRequestSchema):
    "/{ext_dialogue_id}/survey"

    dialogue_id: int = 0
    survey_data: dict[str, Any]


class DialogueTranscriptsRequestSchema(BaseModel):
    """
    /transcripts
    """

    dialogue_ids: list[str]


class DialogueTurnRequestSchema(DialogueRequestSchema):
    """
    "/{ext_dialogue_id}/turn",
    """

    user_turn_start_at: Optional[datetime] = None
    user_turn_end_at: Optional[datetime] = None
    transcript: str
    speaker: SpeakerType
    asr_provider: Optional[str] = AsrType.DEEPGRAM.value
    bot_audio_start_at: Optional[datetime] = None
    bot_audio_end_at: Optional[datetime] = None
    transcript_received_at: Optional[datetime] = None
    transcript_metadata: Optional[list[dict[str, Any]]] = None

    model_config = ConfigDict(use_enum_values=True)


class DialogueV2SimRequestSchema(BaseDialogueRequestSchema):
    """
    /sim_dialogue
    """

    simulation_id: uuid.UUID
    cognito_username: str
    cognito_id: uuid.UUID
    dialogue_type: Optional[str] = DialogueType.SIM.value


########################
# API Response Schemas #
########################


class DialogueTurnResponseSchema(BaseModel):
    """
    /{ext_dialogue_id}/turn
    """

    order_in_turn: int


class DialogueV2DialogueResponseSchema(BaseModel):
    """
    /dialogue
    /sim_dialogue
    """

    ext_dialogue_id: uuid.UUID


class DialogueSurveyResponseSchema(BaseModel):
    """
    /{ext_dialogue_id}/survey
    """

    status: str = "OK"


class DialogueTranscriptDetailResponseSchema(BaseModel):
    """
    Used by DialogueTranscriptsResponseSchema
    """

    order_in_dialogue: int
    speaker: SpeakerType
    transcript: str
    transcript_metadata: Optional[dict[str, Any]] = None
    user_turn_start_at: Optional[datetime] = None
    user_turn_end_at: Optional[datetime] = None
    bot_audio_start_at: Optional[datetime] = None
    bot_audio_end_at: Optional[datetime] = None


class DialogueTranscriptDetailV2ResponseSchema(DialogueTranscriptDetailResponseSchema):
    """
    Used by DialogueTranscriptsV2ResponseSchema
    """

    asr_provider: str
    transcription_date: Optional[datetime] = None


class DialogueTranscriptsResponseSchema(BaseModel):
    """
    /{ext_dialogue_id}/transcripts
    /transcripts
    """

    task_id: str
    transcripts: list[DialogueTranscriptDetailResponseSchema]


class DialogueTranscriptsV2ResponseSchema(BaseModel):
    """
    /{ext_dialogue_id}/transcripts/latest
    """

    task_id: Optional[str]
    transcripts: list[DialogueTranscriptDetailV2ResponseSchema]


class DialogueTranscriptsV3ResponseSchema(DialogueTranscriptsV2ResponseSchema):
    """
    Return task type and transcripts for a given dialogue
    Add ext_dialogue_id to support next and previous browsing

    /transcript/browse/next
    /transcript/browse/previous
    """

    ext_dialogue_id: uuid.UUID


class DialogueTranscriptsV4ResponseSchema(DialogueTranscriptsV3ResponseSchema):
    """
    Add dialogue_type to the response to expose it to the other services, the feedback service will use it first

    /{ext_dialogue_id}/transcripts_with_dialogue_type
    /transcripts_with_dialogue_type
    """

    dialogue_type: DialogueType


class DialogueTranscriptMetadataResponseSchema(BaseModel):
    """
    /{ext_dialogue_id}/{order_in_dialogue}/transcript""
    """

    ext_dialogue_id: uuid.UUID
    turn_id: uuid.UUID
    order_in_dialogue: int
    asr_provider: str
    transcription_date: datetime
    latest: bool
    data: dict[str, Any]
