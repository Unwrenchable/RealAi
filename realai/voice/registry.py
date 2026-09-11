"""Voice backend registry."""


class VoiceRegistry:
    def __init__(self):
        self.asr = {}
        self.tts = {}

    def register_asr(self, backend):
        self.asr[backend.name] = backend

    def register_tts(self, backend):
        self.tts[backend.name] = backend

    def get_asr(self, name):
        if name not in self.asr:
            raise KeyError("Unknown ASR backend: {0}".format(name))
        return self.asr[name]

    def get_tts(self, name):
        if name not in self.tts:
            raise KeyError("Unknown TTS backend: {0}".format(name))
        return self.tts[name]

