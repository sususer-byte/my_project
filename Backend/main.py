from core.runtime import create_runtime
from core.interaction import interaction_loop

if __name__ == "__main__":
    runtime = create_runtime()
    bot = runtime.container.assistant
    runtime.container.app_lifecycle.startup()
    print(runtime.services.list_services())

    try:
        interaction_loop(bot)

    except KeyboardInterrupt:

        pass

    finally:
        runtime.container.app_lifecycle.shutdown()

        print("\nFurgal shutting down.")


