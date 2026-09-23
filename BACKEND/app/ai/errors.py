class AIError(RuntimeError):
    code = "AI_FAILED"

    def __init__(self, message: str):
        super().__init__(f"{self.code}: {message}")


class ModelNotFoundError(AIError):
    code = "MODEL_NOT_FOUND"


class FFmpegNotFoundError(AIError):
    code = "FFMPEG_NOT_FOUND"


class STTError(AIError):
    code = "STT_FAILED"


class DiarizationError(AIError):
    code = "DIARIZATION_FAILED"


class LLMError(AIError):
    code = "LLM_FAILED"


class TaskExtractionError(AIError):
    code = "TASK_EXTRACTION_FAILED"


class OpenAIAPIError(AIError):
    code = "OPENAI_API_ERROR"
