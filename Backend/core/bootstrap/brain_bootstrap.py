from core.brain import Brain

def bootstrap_brain(runtime):
    brain = Brain(runtime.container.provider_manager)
    runtime.container.brain = brain