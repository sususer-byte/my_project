import logging 

logger = logging.getLogger("furgal.lifecycle")

class ApplicationLifecycle: 
    def __init__(self, runtime): 
        self.runtime = runtime 
        self.running = False

    def startup(self): 
        if self.running:
            return 
        logger.info("Starting Furgal runtime..")

        assistant = self.runtime.container.assistant

        if assistant.background_worker:
            assistant.start_background_workers()

        self.running = True

        logger.info("Furgal runtime started")

    def shutdown(self): 
        if not self.running:
            return 
        logger.info("Stopping Furgal runtime....")

        assistant = self.runtime.container.assistant

        if assistant.background_worker:
            assistant.stop_background_workers()

        self.running = False 
        logger.info("Furgal runtime stopped")
