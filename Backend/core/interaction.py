def read_keyboard_input(prompt: str = ">  ") -> str:
    """Read non-empty text from keyboard."""
    user_input = input(prompt)
    while user_input.strip() == "":
        user_input = input(prompt)
    return user_input.strip()


def interaction_loop(bot):
    """Dual-input loop: voice when available, keyboard as fallback."""
    mode = bot.voice.get_mode_description()
    print(f"Furgal AI ready — input mode: {mode}")
    if bot.voice.is_microphone_ready:
        print("Press Enter to speak, or type your message directly.")
    else:
        print("Microphone unavailable — keyboard mode only.")

    while True:
        try:
            user_input = None
            if bot.voice.is_microphone_ready:
                trigger = input(">  ").strip()
                if trigger.lower() in ("quit", "exit", "bye"):
                    break
                if trigger == "":
                    user_input = bot.listen_once(timeout=6.0, phrase_limit=12.0)
                    if user_input:
                        print(f"You (voice): {user_input}")
                    else:
                        print("(No speech detected — type your message)")
                        user_input = read_keyboard_input(">  ")
                else:
                    user_input = trigger
            else:
                user_input = read_keyboard_input(">  ")
                if user_input.lower() in ("quit", "exit", "bye"):
                    break
            reply = bot.chat(user_input)

            print(f"Furgal: {reply}")

        except EOFError:

            break
