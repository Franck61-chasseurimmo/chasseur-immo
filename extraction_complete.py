"""Informations explicites du descriptif, sans service payant ni requête réseau."""
import re
import unicodedata

CHAMPS_COMPLEMENTAIRES = (
    'prix', 'surface_habitable', 'surface_terrain', 'salles_eau',
    'type_maison', 'maison_pierre', 'sous_sol', 'dpe', 'commune',
)
NOMBRES = {'un': 1, 'une': 1, 'deux': 2, 'trois': 3, 'quatre': 4,
           'cinq': 5, 'six': 6, 'sept': 7, 'huit': 8, 'neuf': 9, 'dix': 10}
COMPTE = r'(\d{1,2}|un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)'
MESURE = r'(\d+(?:[ \u00a0\u202f]\d{3})*(?:[.,]\d+)?)'


def normaliser(texte):
    texte = ''.join(c for c in unicodedata.normalize('NFKD', texte.lower())
                    if not unicodedata.combining(c))
    return re.sub(r'[ \t\u00a0\u202f]+', ' ', texte.replace('’', "'").replace('–', '-'))


def nombre(texte):
    return float(re.sub(r'\s+', '', texte).replace(',', '.'))


def extraire_informations(description):
    texte = normaliser(description)
    valeurs, preuves = {}, {}

    def retenir(champ, observations):
        distinctes = {v for v, extrait in observations}
        if len(distinctes) == 1:
            valeurs[champ] = observations[0][0]
            preuves[champ] = [{'valeur': v, 'extrait': e[:600]} for v, e in observations]
        elif observations:
            preuves[champ] = [{'valeur': None, 'extrait': 'Plusieurs valeurs explicites différentes : à vérifier.'}]

    prix = []
    for m in re.finditer(r'\bprix\s*(?:de\s+vente\s*)?(?:affiche\s*)?(?:de\s*)?[:=\-]?\s*' + MESURE + r'\s*(?:€|euros?)', texte):
        avant = texte[max(0, m.start()-40):m.start()]
        apres = texte[m.end():m.end()+50]
        if re.search(r'(?:honoraires|taxe|loyer|travaux|mensualite)', avant[-25:]) or re.match(r'\s*hors\s+honoraires', apres):
            continue
        montant = nombre(m.group(1))
        if 1000 <= montant <= 1000000000:
            prix.append((montant, m.group()))
    if not prix:
        for ligne in texte.splitlines():
            m = re.fullmatch(r'\s*' + MESURE + r'\s*(?:€|euros?)\s*(?:HAI|FAI)?\s*', ligne, re.I)
            if m and 1000 <= nombre(m.group(1)) <= 1000000000:
                prix.append((nombre(m.group(1)), ligne))
    retenir('prix', prix)

    for champ, motifs in (
        ('surface_habitable', [
            r'\bsurface\s+habitable\s*(?:de\s*)?(?:d.environ\s*|environ\s*|:|est\s+de\s+)?\s*' + MESURE + r'\s*m(?:2|²)\b',
            r'\b(?:maison|pavillon|appartement)\s+(?:de\s+|d.environ\s+)?' + MESURE + r'\s*m(?:2|²)\b',
        ]),
        ('surface_terrain', [
            r'\b(?:terrain|parcelle)\s*(?:d.une\s+surface\s+|d.une\s+superficie\s+)?(?:de\s+|:)?\s*' + MESURE + r'\s*m(?:2|²)\b',
        ]),
    ):
        observations = []
        for motif in motifs:
            for m in re.finditer(motif, texte):
                valeur = nombre(m.group(1))
                if 0 < valeur <= 10000000:
                    observations.append((valeur, m.group()))
        retenir(champ, observations)

    # Un total explicitement annoncé reste exploitable après un marqueur d'étage.
    chambres = []
    for motif in [
        r'\b(?:au\s+total|en\s+tout|total\s+de)\s*:?\s*' + COMPTE + r'\s+chambres?\b',
        r'\b' + COMPTE + r'\s+chambres?\s*,?\s+dont\b',
        r'\b\d+\s+pieces\b.{0,70}?\bdont\s+' + COMPTE + r'\s+chambres?\b',
    ]:
        for m in re.finditer(motif, texte):
            phrase = re.split(r'[.!?;]\s+', texte[:m.start()])[-1] + m.group()
            if re.search(r'\b(?:possibilite|projet|pourrait|creer|amenageable)\b', phrase):
                continue
            n = m.group(1)
            chambres.append((int(n) if n.isdigit() else NOMBRES[n], m.group()))
    retenir('chambres', chambres)

    douches = list(re.finditer(r'\b' + COMPTE + r"\s+salles?\s+(?:d[' ]eau|de\s+douches?)\b", texte))
    if len(douches) == 1:
        m = douches[0]
        phrase = re.split(r'[.!?;]\s+', texte[:m.start()])[-1] + m.group()
        if not re.search(r'\b(?:possibilite|projet|pourrait|creer|amenageable|sans|aucune)\b', phrase):
            n = m.group(1)
            retenir('salles_eau', [(int(n) if n.isdigit() else NOMBRES[n], m.group())])

    debut = texte[:400]
    genre = re.search(r'\b(maison|pavillon|appartement|studio)\b', debut)
    if genre:
        prefixe = debut[max(0, genre.start()-25):genre.start()]
        if not re.search(r'\b(?:recherche|cherchons|souhaite|construire)\b', prefixe):
            type_bien = 'appartement' if genre.group(1) == 'studio' else genre.group(1)
            retenir('type_maison', [(type_bien, genre.group())])

    for champ, motif in [
        ('maison_pierre', r'\b(?:maison|batisse|construction)\s+(?:en\s+)?pierres?\b'),
        ('sous_sol', r'\bsous[ -]sol\b'),
    ]:
        observations = []
        for phrase in re.split(r'[.!?;]\s+|\n+', texte):
            if not re.search(motif, phrase):
                continue
            if re.search(r'\b(?:possibilite|projet|pourrait|creer|amenageable|ancien)\b', phrase):
                continue
            negatif = champ == 'sous_sol' and bool(re.search(r'\b(?:sans|pas\s+de|aucun)\s+sous[ -]sol', phrase))
            observations.append((not negatif, phrase))
        retenir(champ, observations)

    retenir('dpe', [(m.group(1).upper(), m.group()) for m in re.finditer(
        r'\bdpe\s*(?:classe\s*|classement\s*)?[:=\-]?\s*([a-g])\b', texte)])
    # Le nom original garde ses accents et sa casse.
    commune = re.search(r"\bsitu[ée]e?\s+[àa]\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ '\-’]{1,65})\s*\((\d{2,3}|\d{5})\)", description, re.I)
    if commune:
        retenir('commune', [(commune.group(1).strip() + ' (' + commune.group(2) + ')', commune.group())])
    return valeurs, preuves
