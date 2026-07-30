import logging


logger = logging.getLogger("furgal.backend.assistant")


class AssistantService:

    def __init__(self, assistant):
        self.assistant = assistant


    def chat(self, message: str):
        try:
            response = self.assistant.chat( message)
            return {
                "success": True,
                "response": response
            }

        except Exception as exc:
            logger.exception("Assistant chat failed")
            return {
                "success": False,
                "error": str(exc)
            }