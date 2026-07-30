from core.lifecycle import ApplicationLifecycle


def bootstrap_lifecycle(runtime):
    runtime.container.app_lifecycle = ApplicationLifecycle(runtime)
