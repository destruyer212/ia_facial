class VoiceSpeaker:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._engine = None

    def say_welcome(self, name: str) -> None:
        self.say(f"Bienvenido {name}")

    def say(self, message: str) -> None:
        if not self.enabled:
            print(message)
            return
        try:
            engine = self._get_engine()
            engine.say(message)
            engine.runAndWait()
        except Exception:
            print(message)

    def _get_engine(self):
        if self._engine is None:
            import pyttsx3

            self._engine = pyttsx3.init()
        return self._engine

