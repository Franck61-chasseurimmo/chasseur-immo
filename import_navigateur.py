"""Import groupé des annonces lues dans le navigateur de l'utilisateur."""
import json
import math

from criteres_bienici import analyser_criteres, CHAMPS
from validation import valider

SCHEMA = 'chasseur-immo-navigateur-v1'
LABELS = {
    'titre': 'Titre', 'prix': 'Prix', 'commune': 'Commune',
    'surface_habitable': 'Surface habitable', 'surface_terrain': 'Terrain',
    'chambres': 'Chambres', 'chambres_rdc': 'Chambres au RDC',
    'salles_eau': 'Salles d’eau', 'garage': 'Garage', 'plain_pied': 'Plain-pied',
    'salle_eau_rdc': 'Salle d’eau au RDC', 'salle_bain_rdc': 'Salle de bains au RDC',
    'type_maison': 'Type', 'maison_pierre': 'Maison en pierre',
    'sous_sol': 'Sous-sol', 'dpe': 'DPE',
}


def identifier_url(url):
    from email_import import extraire_url_bienici
    from leboncoin_import import extraire_url_leboncoin
    from seloger_import import extraire_url_seloger
    from figaro_import import extraire_url_figaro
    for fonction, source in [
        (extraire_url_bienici, "Bien'ici"),
        (extraire_url_leboncoin, 'Leboncoin'),
        (extraire_url_seloger, 'SeLoger'),
        (extraire_url_figaro, 'Figaro Immobilier'),
    ]:
        canonique = fonction(url)
        if canonique:
            return canonique, source
    raise ValueError('Le lien ne correspond pas à une annonce reconnue des quatre sites.')


def _champ_valide(champ, value):
    if champ in ('garage', 'plain_pied', 'salle_eau_rdc', 'salle_bain_rdc', 'sous_sol', 'maison_pierre'):
        return isinstance(value, bool)
    if champ in ('prix', 'surface_habitable', 'surface_terrain', 'chambres', 'chambres_rdc', 'salles_eau'):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            return False
        if champ in ('chambres', 'chambres_rdc', 'salles_eau'):
            return isinstance(value, int) and value <= 100
        return value > 0 and value <= (1000000000 if champ == 'prix' else 10000000)
    if champ == 'type_maison':
        return value in ('maison', 'pavillon', 'appartement', 'maison_pierre')
    if champ == 'dpe':
        return value in ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'non_applicable')
    if champ == 'commune':
        return isinstance(value, str) and 1 <= len(value.strip()) <= 120
    return False


def preparer_fichier(contenu):
    if not isinstance(contenu, bytes) or len(contenu) > 5000000:
        raise ValueError('Choisissez un fichier JSON de moins de 5 Mo.')
    try:
        data = json.loads(contenu.decode('utf-8-sig'))
    except (ValueError, UnicodeError) as exc:
        raise ValueError('Le fichier JSON ne peut pas être lu.') from exc
    if not isinstance(data, dict) or data.get('schema') != SCHEMA or not isinstance(data.get('annonces'), list):
        raise ValueError('Ce fichier ne vient pas de la sélection Chasseur Immo attendue.')
    if not 1 <= len(data['annonces']) <= 100:
        raise ValueError('Le fichier doit contenir entre 1 et 100 annonces.')
    resultat, erreurs, vus = [], [], set()
    for i, item in enumerate(data['annonces'], 1):
        try:
            if not isinstance(item, dict):
                raise ValueError('Fiche non reconnue.')
            url, source = identifier_url(item.get('url'))
            if url in vus:
                continue
            description = item.get('description')
            if not isinstance(description, str) or not 30 <= len(description.strip()) <= 100000:
                raise ValueError('Descriptif absent, trop court ou trop long.')
            valeurs = analyser_criteres({'description': description})
            trace = valeurs['extraction_criteres']
            trace.update(source=source + ' — navigateur', mode='capture_navigateur', url_source=url)
            champs = item.get('champs') or {}
            if not isinstance(champs, dict):
                raise ValueError('Caractéristiques structurées non reconnues.')
            for champ, value in champs.items():
                if champ in CHAMPS and _champ_valide(champ, value):
                    if champ in valeurs and valeurs[champ] != value:
                        valeurs.pop(champ)
                        trace['preuves'][champ] = [{
                            'valeur': None,
                            'extrait': 'Le descriptif et les caractéristiques de la page diffèrent : à vérifier.',
                        }]
                    else:
                        valeurs[champ] = value
                        trace['preuves'][champ] = [{
                            'valeur': value,
                            'extrait': 'Caractéristique indiquée sur la page ouverte dans le navigateur.',
                        }]
            titre = item.get('titre')
            if isinstance(titre, str) and titre.strip():
                valeurs['titre'] = titre.strip()[:400]
            valeurs.update(url=url, source=source)
            # Contrôle final des nombres et de la cohérence RDC/total.
            if valeurs.get('chambres') is not None and valeurs.get('chambres_rdc') is not None and valeurs['chambres_rdc'] > valeurs['chambres']:
                valeurs.pop('chambres_rdc')
                trace['preuves']['chambres_rdc'] = [{
                    'valeur': None,
                    'extrait': 'Nombre au RDC incompatible avec le total : à vérifier.',
                }]
            valeurs = valider(valeurs)
            resultat.append(valeurs)
            vus.add(url)
        except (ValueError, TypeError) as exc:
            erreurs.append(f'Annonce {i} : {exc}')
    return resultat, erreurs


def importer_selection(db, annonces):
    from services import recalculer

    bilan = dict(
        nouvelles=0, completees=0, champs_remplis=0, archives=0,
        differences=[], erreurs=[], matching_erreurs=0,
    )
    index = {}
    for bien in db.get_annonces():
        try:
            url, _ = identifier_url(bien.get('url'))
            index[url] = bien
        except (ValueError, TypeError):
            continue
    for i, annonce in enumerate(annonces, 1):
        try:
            ancienne = index.get(annonce['url'])
            if ancienne and ancienne.get('statut_annonce', 'disponible') != 'disponible':
                bilan['archives'] += 1
                continue
            if ancienne:
                changements = {
                    'description': annonce['description'],
                    'extraction_criteres': annonce['extraction_criteres'],
                }
                for champ, valeur in annonce.items():
                    if champ in changements:
                        continue
                    if ancienne.get(champ) is None or ancienne.get(champ) == '':
                        changements[champ] = valeur
                    elif champ in LABELS and ancienne[champ] != valeur:
                        bilan['differences'].append(
                            f'Annonce {i} — {LABELS[champ]} : valeur existante conservée '
                            f'({ancienne[champ]}), nouvelle valeur extraite ({valeur}).'
                        )
                if ancienne.get('url') != annonce['url']:
                    changements['url'] = annonce['url']
                total = ancienne.get('chambres') if ancienne.get('chambres') is not None else changements.get('chambres')
                rdc = ancienne.get('chambres_rdc') if ancienne.get('chambres_rdc') is not None else changements.get('chambres_rdc')
                if total is not None and rdc is not None and rdc > total:
                    changements.pop('chambres', None)
                    changements.pop('chambres_rdc', None)
                    bilan['differences'].append(
                        f'Annonce {i} — nombre de chambres au RDC incompatible : valeurs connues conservées.'
                    )
                bien = db.enregistrer('annonces', changements, ancienne['id'])
                if not bien:
                    raise RuntimeError('Enregistrement non confirmé.')
                bilan['completees'] += 1
                bilan['champs_remplis'] += sum(k in LABELS for k in changements)
            else:
                bien = db.insert_annonce(dict(
                    annonce,
                    type_annonceur='inconnu',
                    statut_annonce='disponible',
                ))
                if not bien:
                    raise RuntimeError('Enregistrement non confirmé.')
                bilan['nouvelles'] += 1
                bilan['champs_remplis'] += sum(k in LABELS for k in annonce)
            if not bien:
                raise RuntimeError('Enregistrement non confirmé.')
            index[annonce['url']] = bien
            try:
                recalculer(db, annonces=[bien])
            except Exception:
                bilan['matching_erreurs'] += 1
        except Exception:
            bilan['erreurs'].append(
                f'Annonce {i} : enregistrement interrompu. Relancez le fichier pour reprendre.'
            )
    return bilan
