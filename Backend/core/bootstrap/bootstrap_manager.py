import logging

from core.bootstrap.provider_bootstrap import bootstrap_provider
from core.bootstrap.brain_bootstrap import bootstrap_brain
from core.bootstrap.memory_bootstrap import bootstrap_memory
from core.bootstrap.action_bootstrap import bootstrap_action
from core.bootstrap.cognition_bootstrap import bootstrap_cognition
from core.bootstrap.assistant_bootstrap import bootstrap_assistant
from core.bootstrap.lifecycle_bootstrap import bootstrap_lifecycle


logger = logging.getLogger("furgal.bootstrap")


def bootstrap_all(runtime):

    logger.info("Starting Furgal bootstrap process")

    bootstrap_provider(runtime)
    bootstrap_brain(runtime)
    bootstrap_memory(runtime)
    bootstrap_action(runtime)
    bootstrap_cognition(runtime)
    bootstrap_assistant(runtime)
    bootstrap_lifecycle(runtime)


    logger.info("Furgal bootstrap completed")