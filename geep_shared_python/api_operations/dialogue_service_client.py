from geep_shared_python.schemas.shared_schemas import SharedSettings
from geep_shared_python.api_operations.api_operations import (
    api_request,
    SupportedMethods,
)
import geep_shared_python.schemas.dialogue_service as ds
from typing import Optional, Any

settings = SharedSettings()


class DialogueServiceClient:
    def __init__(self):
        dialogue_service_host = settings.dialogue_service_host
        dialogue_service_port = settings.dialogue_service_port

        self._service_url = f"http://{dialogue_service_host}:{dialogue_service_port}"

    def post_dialogue(
        self, request_body: ds.DialogueV2RequestSchema
    ) -> ds.DialogueV2DialogueResponseSchema:
        url = f"{self._service_url}/v2/dialogue"

        response = api_request(
            url=url, method=SupportedMethods.POST, body=request_body.model_dump()
        )

        validated_response = ds.DialogueV2DialogueResponseSchema.model_validate(
            response
        )

        return validated_response

    def post_sim_dialogue(
        self, request_body: ds.DialogueV2SimRequestSchema
    ) -> ds.DialogueV2DialogueResponseSchema:
        url = f"{self._service_url}/v2/sim_dialogue"

        response = api_request(
            url=url, method=SupportedMethods.POST, body=request_body.model_dump()
        )

        validated_response = ds.DialogueV2DialogueResponseSchema.model_validate(
            response
        )

        return validated_response

    def post_turn(
        self, request_body: ds.DialogueTurnRequestSchema
    ) -> ds.DialogueTurnResponseSchema:
        url = f"{self._service_url}/v2/sim_dialogue"

        response = api_request(
            url=url, method=SupportedMethods.POST, body=request_body.model_dump()
        )

        validated_response = ds.DialogueTurnResponseSchema.model_validate(response)

        return validated_response

    def get_transcripts_browse_next(
        self, ext_dialogue_id: Optional[str] = None
    ) -> ds.DialogueTranscriptsV3ResponseSchema:
        url = f"{self._service_url}/transcripts/browse/next"

        if ext_dialogue_id:
            url = f"{url}?ext_dialogue_id={ext_dialogue_id}"

        response = api_request(url=url, method=SupportedMethods.GET)

        validated_response = ds.DialogueTranscriptsV3ResponseSchema.model_validate(
            response
        )

        return validated_response

    def get_transcripts_browse_previous(
        self, ext_dialogue_id: Optional[str] = None
    ) -> ds.DialogueTranscriptsV3ResponseSchema:
        url = f"{self._service_url}/transcripts/browse/previous"

        if ext_dialogue_id:
            url = f"{url}?ext_dialogue_id={ext_dialogue_id}"

        response = api_request(url=url, method=SupportedMethods.GET)

        validated_response = ds.DialogueTranscriptsV3ResponseSchema.model_validate(
            response
        )

        return validated_response

    def get_original_dialogue_transcript(
        self, ext_dialogue_id: str
    ) -> ds.DialogueTranscriptsResponseSchema:
        url = f"{self._service_url}/v1/{ext_dialogue_id}/transcripts"

        response = api_request(url=url, method=SupportedMethods.GET)

        validated_response = ds.DialogueTranscriptsResponseSchema.model_validate(
            response
        )

        return validated_response

    def get_latest_dialogue_transcript(
        self, ext_dialogue_id: str
    ) -> ds.DialogueTranscriptsV2ResponseSchema:
        url = f"{self._service_url}/v1/{ext_dialogue_id}/transcripts/latest"

        response = api_request(url=url, method=SupportedMethods.GET)

        validated_response = ds.DialogueTranscriptsV2ResponseSchema.model_validate(
            response
        )

        return validated_response

    def get_dialogue_transcripts_list(
        self, request_body: ds.DialogueTranscriptsRequestSchema
    ) -> list[ds.DialogueTranscriptsResponseSchema]:
        url = f"{self._service_url}/v1/transcripts"

        response = api_request(
            url=url, method=SupportedMethods.POST, body=request_body.model_dump()
        )

        validated_response = [
            ds.DialogueTranscriptsResponseSchema.model_validate(r) for r in response
        ]

        return validated_response

    def insert_new_transcript(
        self,
        ext_dialogue_id: str,
        order_in_dialogue: int,
        asr_provider: str,
        request_body: dict[str, Any],
    ) -> ds.DialogueTranscriptMetadataResponseSchema:
        url = f"{self._service_url}/v1/transcripts"

        response = api_request(url=url, method=SupportedMethods.POST, body=request_body)

        validated_response = ds.DialogueTranscriptMetadataResponseSchema.model_validate(
            response
        )

        return validated_response
