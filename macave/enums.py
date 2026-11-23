from enum import Enum


class TypeVin(Enum):
    ROUGE = "rouge"
    BLANC = "blanc"
    ROSE = "rose"
    EFFERVESCENT = "effervescent"

    def libelle(self) -> str:
        # Nom affiché
        noms = {"rouge": "Rouge", "blanc": "Blanc", "rose": "Rosé", "effervescent": "Effervescent"}
        return noms[self.value]


class StatutBouteille(Enum):
    EN_STOCK = "en_stock"
    ARCHIVEE = "archivee"
