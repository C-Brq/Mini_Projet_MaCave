def texte_note(note):
    # Note sur 20, ou « Non évalué » sans note
    if note is None:
        return "Non évalué"
    note = round(note, 1)           # une seule décimale
    if note == int(note):           # 15.0 devient 15
        note = int(note)
    return str(note) + " / 20"


def texte_prix(prix):
    # Prix avec deux décimales
    return "%.2f €" % prix


def texte_date(une_date):
    # Date au format JJ/MM/AAAA
    return une_date.strftime("%d/%m/%Y")


def pourcentage_entier(taux):
    # Taux en pourcentage entier
    return round(taux * 100)


def texte_pourcentage(taux):
    # Taux en pourcentage avec une décimale
    return "%.1f %%" % (taux * 100)   # %% écrit un vrai signe %
