from .kyber_pke_subfunctions import Pke_subfunctions
from .kyber_kem_subfunctions import Kem_subfunctions


class Kyber_subfunctions:
    def __init__(self, kyber) -> None:
        self.kyber = kyber
        self.pke = Pke_subfunctions(kyber)
        self.kem = Kem_subfunctions(kyber)

    def load_dll(self):
        self.pke.load_dll()
        self.kem.load_dll()
