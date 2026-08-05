"""Web3 backend registry."""


class Web3Registry:
    def __init__(self):
        self.backends = {}

    def register(self, backend):
        self.backends[backend.name] = backend

    def get(self, name):
        if name not in self.backends:
            raise KeyError("Unknown web3 backend: {0}".format(name))
        return self.backends[name]

