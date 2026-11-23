from macave.validation import nettoyer_texte, verifier_entier_positif


class Etagere:
    def __init__(self, nom: str, capacite_max: int, id=None):
        verifier_entier_positif(capacite_max, "La capacité")
        self.id = id
        self.nom = nettoyer_texte(nom, "Le nom de l'étagère")
        self.capacite_max = capacite_max
        self.bouteilles = []  # bouteilles en stock seulement

    @property
    def occupation(self) -> int:
        return len(self.bouteilles)

    def places_libres(self) -> int:
        return self.capacite_max - self.occupation

    def taux_occupation(self) -> float:
        return self.occupation / self.capacite_max

    def est_vide(self) -> bool:
        return self.occupation == 0

    def modifier_capacite(self, capacite_max: int) -> None:
        verifier_entier_positif(capacite_max, "La capacité")
        if capacite_max < self.occupation:
            raise ValueError("La capacité ne peut pas être inférieure à l'occupation actuelle.")
        self.capacite_max = capacite_max

    def accueillir(self, bouteilles: list) -> None:
        # Tout ou rien selon la place libre
        if len(bouteilles) > self.places_libres():
            raise ValueError("Capacité de l'étagère dépassée.")
        for bouteille in bouteilles:
            self.bouteilles.append(bouteille)
            bouteille.etagere = self

    def retirer(self, bouteille) -> None:
        self.bouteilles.remove(bouteille)
        if bouteille.etagere is self:
            bouteille.etagere = None
