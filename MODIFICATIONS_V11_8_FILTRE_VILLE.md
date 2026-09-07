# V11.8 — Filtre par ville dans la section Alertes

## Besoin

ARMA opère par contrat de gestion déléguée, ville par ville. « 12 alertes
négatives » ne dit rien d'actionnable ; « 9 alertes négatives à Casablanca »
désigne un contrat et une équipe.

## Difficulté

Le nom de la ville n'existe dans **aucune colonne** de la base. Il apparaît en
clair à trois endroits, selon le type d'alerte :

| Endroit | Exemple réel |
|---|---|
| Texte du commentaire | « C'est très sale Casablanca les poubelles sont catastrophiques » |
| Titre de la publication | « Propreté urbaine : El Jadida revoit sa copie » |
| URL de la source | `leseco.ma/maroc/kenitra-mecomar-decroche-le-contrat.html` |

## Détection — `backend/processing/city_detection.py`

53 villes marocaines et une centaine de quartiers, chacun avec ses variantes :
français, arabe, surnoms (`Casa`), slugs d'URL (`el-jadida`, `beni-mellal`).

**Ordre de recherche**, du plus spécifique au moins spécifique :

1. **le texte de l'alerte** — un commentaire qui cite une ville parle de cette
   ville, même publié sous un article consacré à une autre ;
2. **son titre** ;
3. **le texte de la publication parente** — héritage, voir plus bas ;
4. **le titre de la publication parente** ;
5. **l'URL**, où la ville apparaît souvent en slug.

### La ville est le plus souvent citée indirectement

Trois mécanismes ont été nécessaires, parce qu'un commentaire nomme rarement sa
ville :

**Quartiers et lieux-dits.** « mazbala fi Aïn Sebaa » parle de Casablanca sans
jamais l'écrire. `NEIGHBOURHOOD_ALIASES` associe une centaine de quartiers et
de places à leur ville : Aïn Sebaa, Sidi Moumen, Derb Sultan, place du 16
Novembre pour Casablanca ; Guéliz et Jamaa el Fna pour Marrakech ; Tabriquet et
Bettana pour Salé — ces deux derniers rattrapant Salé sans passer par son nom
ambigu. Les noms équivoques (Bourgogne, Californie) sont volontairement exclus.

**Particules arabes collées.** En arabe, `و ف ب ل ك` s'attachent au mot suivant :
« فعين السبع » (« à Aïn Sebaa ») ne contient pas « عين السبع » entouré d'espaces.
La recherche tolère donc une particule accolée devant un alias arabe. Sans cela,
une grande partie des commentaires arabes passait à côté de sa ville.

**Héritage de la publication parente.** Un commentaire qui ne nomme aucun
territoire hérite de celui de son post. `parent.title` vaut souvent le seul nom
du média (« Le360 ») : c'est le **texte** du post qui porte la ville, d'où
`parent_text` avant `parent_title`.

Le champ `city_evidence` conserve le mot exact ayant déclenché le rattachement
(« ain sebaa », « place de 16 novembre »), affiché en infobulle. Rattacher un
quartier à sa ville sans le montrer paraîtrait arbitraire.

Le champ `city_source` indique lequel des trois a répondu, et l'interface
l'affiche (« Casablanca · texte de l'alerte ») pour que l'utilisateur puisse
vérifier plutôt que faire confiance.

### Normalisation

Minuscules, accents retirés, ponctuation réduite à des espaces — ce qui
transforme `el-jadida` en `el jadida` et permet de lire un slug d'URL. Les
variantes d'alef arabe (`أ إ آ`) sont ramenées à `ا` et les diacritiques retirés.
Les alias sont cherchés **entre deux espaces** : `safiarrive` ne déclenche pas
Safi.

### Le piège « sale » / « Salé »

Une fois les accents retirés, `salé` et `sale` sont le même mot — et « c'est
sale » est l'expression la plus fréquente des plaintes déchets. Rattacher ces
plaintes à la ville de Salé fausserait tout le filtre.

`Salé` est donc le seul nom exigeant la **forme accentuée exacte**. On manque
les graphies « Sale » sans accent, ce qui est très largement préférable à
l'inverse. Vérifié sur vos données : « C'est très sale Casablanca » est bien
rattaché à Casablanca.

## Villes multiples — une alerte, une ville

Une alerte est rattachée à **une seule ville** : celle trouvée par la source la
plus spécifique. C'est ce qui garantit l'invariant attendu par le métier :

```
somme des compteurs par ville  +  ville non détectée  =  total des alertes
```

Un premier essai comptait l'alerte sous chacune des villes qu'elle cite. La
répartition dépassait alors le nombre réel d'alertes (43 comptées pour 39
affichées sur la semaine 30), ce qui la rendait inexploitable : impossible de
dire « Casablanca représente un tiers de nos alertes » si les parts totalisent
plus que le tout.

Les autres villes citées restent connues — champ `cities`, affiché en infobulle
sur la pastille (« Cite aussi : Casablanca »). Elles informent, elles ne
comptent pas.

## Interface

Un second menu déroulant dans la barre de filtre de la section Alertes,
construit à partir des alertes **de la semaine affichée**, avec le nombre
d'alertes par ville, les plus nombreuses en tête :

```
Toutes les villes (39) · Casablanca (13) · Bouskoura (1) · El Jadida (1)
· Marrakech (1) · Tanger (1) · Ville non détectée (22)
```

- Le menu est reconstruit à chaque changement de semaine ; si la ville choisie
  n'a plus d'alerte, le filtre se remet sur « Toutes les villes ».
- L'entrée **Ville non détectée** isole les alertes sans territoire identifiable,
  utile pour repérer ce que la détection laisse passer.
- Une liste vide sous filtre affiche « Aucun signal rattaché à X sur cette
  semaine », et non « aucune alerte » — la nuance évite un faux diagnostic.
- Le titre de la section rappelle la ville active.

## Résultats sur la base

Effet de la détection indirecte sur les alertes non rattachées :

| Semaine | Avant | Après |
|---|---|---|
| 20/07 → 26/07 | 22 non détectées sur 46 | **0** |
| 27/07 → 02/08 | 6 non détectées sur 8 | **0** |
| 17/08 → 23/08 | 0 sur 6 | 0 |

Semaine du 20 au 26 juillet : 41 Casablanca, puis Essaouira, Marrakech, Tanger,
El Jadida et Bouskoura à 1 chacune. La moitié des rattachements vient du texte
de l'alerte, l'autre de la publication parente.

Le filtre serveur `?city=` rend exactement le compteur annoncé, vérifié ville
par ville.

## Compromis assumé sur l'héritage

L'héritage rattache **tous** les commentaires d'un post à la ville de ce post,
y compris les commentaires purement génériques (« Manque d'éducation »). C'est
défendable sur le fond — une plainte sous un article consacré à Casablanca
relève bien du contrat de Casablanca — mais ce n'est pas une preuve directe.

L'interface le signale plutôt que de le masquer : la pastille d'une ville
héritée est d'une nuance différente et porte la mention « publication parente ».
Un rattachement direct affiche « texte de l'alerte ».

Pour revenir à un rattachement strictement explicite, il suffit de ne plus
passer `parent_text` ni `parent_title` à `detect_city` dans
`backend/api/alerts.py`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `backend/processing/city_detection.py` | **nouveau** — détection, normalisation, liste de référence |
| `backend/api/alerts.py` | rattachement sur les deux routes, paramètre `?city=` |
| `backend/api/schemas.py` | `city`, `city_source`, `city_source_label`, `cities` |
| `frontend/ReputationSocialeARMA.html` | menu déroulant, pastille, filtrage |
| `tests/test_v11_8_filtre_ville.py` | **nouveau** — 24 tests : invariant de répartition, quartiers, arabe, héritage |

## Limite connue

La détection reste lexicale. Un commentaire isolé qui décrit un quartier absent
de la liste, sans publication parente, reste « non détecté ». Pour l'étendre,
ajoutez le quartier dans `NEIGHBOURHOOD_ALIASES` sous sa ville — le test
`test_neighbourhood_aliases_are_unambiguous` refusera un nom déjà revendiqué
par une autre ville.
