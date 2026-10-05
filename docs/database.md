# Documentation de la base de données - Le Seizième

## Vue d'ensemble

Base de données PostgreSQL pour la gestion du personnel événementiel.
Architecture relationnelle normalisée pour ~150 serveurs, plusieurs villes et de nombreux événements.

## Tables

### cities
Référentiel des villes.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| name | VARCHAR(100) | Nom unique de la ville |
| latitude | NUMERIC(10,8) | Position de référence de la ville (nullable) |
| longitude | NUMERIC(11,8) | Position de référence de la ville (nullable) |
| created_at | TIMESTAMP | Date de création |

**Coordonnées de référence** : `latitude`/`longitude` placent la ville sur la carte
lorsque l'événement n'a pas encore ses propres coordonnées. Le couple est
contraint (`latitude` et `longitude` sont tous deux nuls ou tous deux renseignés,
et les plages -90..90 / -180..180 sont vérifiées), donc une demi-coordination ne
peut jamais être interprétée comme l'origine (0, 0).

Ces colonnes sont **volontairement laissées vides** : aucun remplissage
automatique n'a été effectué, car inventer une position pour une ville produirait
de fausses distances. Tant qu'elles sont nulles, le système retombe sur la
valeur technique globale (`DEFAULT_EVENT_LATITUDE` / `DEFAULT_EVENT_LONGITUDE`)
et signale la position comme approximative.

Résolution de la position d'un événement, dans cet ordre :

1. les coordonnées de l'événement lui-même → position exacte ;
2. les coordonnées de sa ville → position approximative ;
3. la valeur technique globale → position approximative.

La position GPS personnelle d'un serveur n'est **jamais** utilisée comme position
de lieu. Les API exposent uniquement le booléen `has_exact_location` ; le détail
de la source utilisée est interne.

Migration : `database/migrations/20260930_city_reference_coordinates.sql`
(idempotente).

### servers
Serveurs événementiels.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| first_name | VARCHAR(100) | Prénom |
| last_name | VARCHAR(100) | Nom |
| phone | VARCHAR(20) | Téléphone |
| email | VARCHAR(255) | Email unique |
| gender | gender_type | Genre |
| city_id | UUID | Ville de rattachement (FK cities) |
| years_experience | INTEGER | Années d'expérience |
| is_active | BOOLEAN | Compte actif |
| uniform_size | server_uniform_size | Taille de tenue, **nullable** (étape 24C-D-9) |
| profile_photo | TEXT | **Hérité, inutilisé.** Conservé pour compatibilité ; voir `server_files` |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

**IMPORTANT** : L'adresse exacte du domicile n'est pas stockée dans cette table.

#### uniform_size (étape 24C-D-9)

Énumération `server_uniform_size` : `XS`, `S`, `M`, `L`, `XL`, `XXL`, `XXXL`
(déclarée du plus petit au plus grand, l'ordre de l'énumération est donc
utilisable comme ordre de tri).

| Point | Choix |
|-------|-------|
| NULLABLE | Oui, **sans DEFAULT**. Les serveurs existants n'ont pas de taille relevée ; une valeur par défaut affirmerait une taille que personne n'a mesurée, et la rendrait indiscernable d'une mesure réelle. `NULL` = « non renseignée ». |
| Type | Énumération PostgreSQL, pas du texte libre. `L`, `l`, `GRAND` et `L ` ne peuvent pas coexister pour la même taille, et une valeur hors liste est refusée par la base autant que par l'API. |
| Portée | Donnée opérationnelle : exposed dans l'authentification de gestion des serveurs (détail, liste, création, mise à jour) et dans `assignments[].uniform_size` du contrat d'impression d'un événement. |
| Mise à jour | `PATCH /api/servers/{id}` avec `uniform_size: null` **efface** la valeur ; omettre la clé la laisse intacte. Les autres champs conservent leur sémantique existante (« null = absent »). |

Aucune clé étrangère : la taille est une propriété de la personne, pas une
référence à un catalogue d'uniformes.

Migration : `database/migrations/20261004_server_uniform_size.sql` (idempotente).
À appliquer **avant** le code qui lit ou écrit `servers.uniform_size`.

### server_files
Fichiers binaires rattachés à un serveur (photos de profil **et** documents
d'attestation). **Étapes 24C-D-5, 24C-D-6 et 24C-D-11.**

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| server_id | UUID | Serveur (FK servers, ON DELETE CASCADE) |
| file_type | server_file_type | Type de fichier (`PROFILE_PHOTO`, `ATTESTATION`) |
| content | BYTEA | Contenu binaire |
| mime_type | VARCHAR(100) | Type MIME vérifié |
| original_filename | VARCHAR(255) | Nom d'origine, nettoyé (facultatif) |
| file_size | INTEGER | Taille en octets |
| is_current | BOOLEAN | Fichier actuellement actif |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

**Stockage BYTEA.** Les octets résident dans PostgreSQL. Aucun stockage objet
externe, aucune URL publique, aucun lien signé : il n'existe aucun moyen
d'adresser un fichier sans passer par un endpoint authentifié.

**Pas de métadonnées GPS.** La table ne contient aucune colonne de localisation.
Une photo n'est jamais associée à une position.

**Deux sémantiques de cycle de vie, une seule table.** Le comportement dépend de
`file_type` :

- `PROFILE_PHOTO` — un seul fichier courant. Uploader une nouvelle photo ne
  supprime pas l'ancienne : l'ancienne passe à `is_current = FALSE` et reste en
  base.
- `ATTESTATION` — documents **append-only**. Un serveur peut légitimement
  détenir plusieurs documents courants, un document rejeté reste consultable pour
  l'audit, et un document remplacé n'est jamais écrasé.

L'index unique partiel qui garantissait l'unicité du fichier courant est donc
**restreint aux photos** : `idx_server_files_unique_current_photo` porte le
prédicat `WHERE is_current AND file_type = 'PROFILE_PHOTO'`. Un index portant
seulement `WHERE is_current` — son état avant cette étape — rejetterait à tort le
second document d'attestation d'un serveur par violation d'unicité.

Le prédicat ne cite que l'étiquette `PROFILE_PHOTO`, préexistante : l.index peut
donc être évalué dans la transaction qui ajoute la nouvelle valeur d'énumération
(PostgreSQL interdit d'utiliser une étiquette non encore committée dans le DDL).
La comparaison est une égalité d'énumération, pas un transtypage `::text`, car un
prédicat d'index ne peut référencer que des expressions `IMMUTABLE` et le
transtypage enum→text ne l'est pas.

**Contraintes.** Contenu non vide ; `file_size` doit être égal à
`octet_length(content)` ; `mime_type` limité à PDF / JPEG / PNG / WebP ; le nom de
fichier ne peut contenir de séparateur de chemin.

**Validation par contenu, jamais par extension.** Le service compare les octets
d'en-tête (*magic bytes*) au type MIME déclaré. Le nom de fichier et le
`Content-Type` du client peuvent refuser un fichier, jamais l'authentifier.
Tailles maximales distinctes par type : `MAX_PROFILE_PHOTO_BYTES` (2 Mio) et
`MAX_ATTESTATION_BYTES` (5 Mio).

**Légalité de `servers.profile_photo`.** Cette colonne TEXT est héritée : aucun
code ne la lit ni ne l'écrit. Elle n'est pas supprimée à cette étape et
`server_files` fait désormais autorité. Aucune photo n'est rétroportée depuis
`servers.profile_photo`.

Migration : `database/migrations/20261001_server_files.sql` (idempotente).
Étape 24C-D-6 : `database/migrations/20261002_server_attestations.sql`
(idempotente).

#### Optimisation des photos de profil — étape 24C-D-11

L'audit en lecture seule de l'étape 24C-D-10 a montré que le chemin
*métadonnées* de la fiche d'impression était déjà efficace, et qu'un
`get_event_print_data()` exécutait 8 instructions SQL constantes sur une seule
connexion, sans boucle par serveur. Il est resté intact.

Le coût réel était la **livraison des images**. La fiche d'impression émet une
requête authentifiée par serveur disposant d'une photo et attend la toutes avant
d'imprimer ; chaque réponse transportait la photo à sa taille d'*upload* d'origine
(jusqu'à 2 Mio). Cent serveurs sur un téléphone, c'étaient jusqu'à 200 Mio.

La correction se fait donc à l'**écriture**, pas à la lecture : réduire une fois,
stocker la version réduite, et livrer par l'existant un document qu'une fiche
d'impression peut réellement utiliser.

- **Aucune migration.** `PROFILE_PHOTO` contient la représentation optimisée, qui
  fait autorité. Aucun consuming n'a besoin de l'original : la photo n'est rendue
  qu'en vignette, et l'audit n'a trouvé aucun autre lecteur de pleine résolution.
  La base ne contenait aucune photo courante. Il n'y a donc ni rétroportage, ni
  colonne d'original, ni table de vignettes.
- **512 px de côté maximal** (`PROFILE_PHOTO_MAX_DIMENSION`). La fiche imprime la
  photo en 22 × 27 mm, soit environ 260 × 319 px à 300 DPI ; le plus grand usage
  à l'écran est 128 px CSS, soit 384 px à 3×. 512 px couvre les deux avec une
  marge de résolution, sans jamais agrandir : une image déjà plus petite est
  conservée telle quelle.
- **JPEG qualité 82** (`PROFILE_PHOTO_JPEG_QUALITY`), rapport d'aspect préservé
  par une unique échelle de boîte englobante — pas de recadrage, pas de
  déformation.
- **Métadonnées supprimées.** Le ré-encodage ne transmet ni `exif`, ni
  `icc_profile`, ni `xmp` : les tags GPS, numéros de série d'appareil, modèles
  d'appareil et profils de couleur disparaissent. L'orientation EXIF est
  appliquée aux pixels *avant* d'être abandonnée, pour qu'une photo de téléphone
  prise en portrait ne soit pas stockée à l'envers. Une transparence est aplatie
  sur fond blanc plutôt que rendue en noir.
- **Jamais plus volumineux.** Si le ré-encodage ne réduit pas la taille, les
  octets d'origine sont conservés. L'optimisation ne peut donc qu'abaisser le
  payload et le stockage, jamais les augmenter.
- **La validation passe en premier, sur les octets d'origine.** La liste blanche
  de types et le plafond de 2 Mio décrivent donc toujours ce que le client a
  réellement envoyé, et aucun upload valide ne peut devenir invalide du fait de
  cette étape. `file_size` est ensuite mesuré sur les octets effectivement
  persistés, ce qui préserve la contrainte `file_size = octet_length(content)`.
- **Optimisation au mieux, jamais un motif de refus.** Si Pillow ne peut pas
  décoder la charge utile — tronquée, exotique, ou une bombe de décompression
  arrêtée par le garde-fou de Pillow lui-même, auquel cas les octets d'origine
  sont conservés sans jamais être développés — le service stocke l'original.
- **Les documents d'attestation ne sont jamais touchés.** Ce sont des preuves et
  sont préservés octet pour octet ; seule la branche `PROFILE_PHOTO` est
  optimisée.

**Cache privé avec revalidation.** L'en-tête `Cache-Control` passe de
`private, no-store, max-age=0` à `private, no-cache` : le navigateur peut
conserver les octets, mais doit les revalider avant toute réutilisation. Le
`ETag` est une empreinte SHA-256 tronquée à 128 bits **du contenu**, jamais de
l'identifiant de ligne, donc rien d'interne ne fuite dans un en-tête renvoyé au
client. Un `If-None-Match` correspondant produit un `304` sans corps. Cette
politique ne contourne pas l'authentification : la dépendance d'autorisation
s'exécute avant le gestionnaire de route, donc un `304` n'est jamais remis à un
appelant non authentifié, et un rechargement ne dispense jamais du jeton.

**Une seule connexion par requête photo.** Le point de terminaison réutilise la
connexion qu'il détient déjà pour vérifier l'existence du serveur au lieu d'en
acquérir une seconde, ramenant une requête photo de deux acquisitions à une.
Les deux fonctions de service acceptent une connexion existante ; sans argument,
elles en acquièrent une comme auparavant.

**Endpoint groupé volontairement différé.** La correction est déjà atteignable
sans lui. Une livraison groupée pour une fiche d'impression reste possible si la
mesure le justifie un jour, mais elle n'est pas implémentée à cette étape.

Mesures (Chromium, feuille d'impression de production, photos 2400 × 3200
réelles) : 50 serveurs passent de 82,53 Mio à 5,19 Mo (facteur 15,9) et 100
serveurs de 165,07 Mio à 10,39 Mo (facteur 15,9). Sur une connexion 4G
profilée (9 Mbit/s, 170 ms), la fiche de 100 serveurs passe de 28,60 s à
11,37 s. Le gabarit d'audit de l'étape D-10, rejoué tel quel, donne des temps
identiques avant et après (28,47 s contre 28,60 s pour 100 serveurs), ce qui
démontre l'absence de régression.

### server_attestations
Attestations professionnelles d'un serveur. **Étape 24C-D-6.**

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| server_id | UUID | Serveur (FK servers, ON DELETE CASCADE) |
| file_id | UUID | Document (FK server_files, ON DELETE RESTRICT) |
| qualification_name | VARCHAR(200) | Intitulé de la qualification, non vide |
| issuing_organization | VARCHAR(200) | Organisme émetteur (facultatif) |
| issued_on | DATE | Date de délivrance (facultatif) |
| expires_on | DATE | Date d'expiration (facultatif) |
| status | attestation_status | `PENDING` / `VERIFIED` / `REJECTED` / `SUPERSEDED` |
| rejection_reason | TEXT | Motif de rejet (obligatoire si `REJECTED`) |
| verified_at | TIMESTAMP | Date de vérification |
| verified_by | UUID | Vérificateur (FK users) |
| superseded_by_id | UUID | Attestation qui remplace celle-ci |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

**Append-only.** Un envoi crée une ligne `PENDING` et ne modifie jamais une ligne
existante. Un renouvellement de qualification est donc un nouvel envoi suivi d'un
remplacement explicite de l'ancien document, jamais une réécriture.

**Un envoi ne valide jamais automatiquement.** Le seul moyen d'obtenir le statut
`VERIFIED` est une décision explicite d'un MANAGER ou d'un ADMIN. Le champ
`counts_as_verified_qualification` valant vrai uniquement pour `VERIFIED`, seul lui
doit piloter un décompte de qualifications.

**Transitions autorisées.**

| Depuis | Vers | Condition |
|--------|------|-----------|
| `PENDING` | `VERIFIED` | MANAGER/ADMIN ; le vérificateur est l'utilisateur authentifié, jamais un choix du client |
| `PENDING` | `REJECTED` | MANAGER/ADMIN ; motif non vide obligatoire |
| `PENDING` | `SUPERSEDED` | MANAGER/ADMIN |
| `VERIFIED` | `SUPERSEDED` | MANAGER/ADMIN ; **le document de remplacement est obligatoire** |

`REJECTED` et `SUPERSEDED` sont terminaux. Il n'existe délibérément **aucune**
transition `VERIFIED → REJECTED` ni `VERIFIED → PENDING` : une attestation
vérifiée ne peut pas être révoquée ni rétrogradée à cette étape. Une révocation
exigerait une décision et une justification propres, hors périmètre ici.

`VERIFIED → SUPERSEDED` n'est pas une révocation : le document reste vérifié avec
son `verified_at` et son `verified_by` conservés comme piste d'audit, et il pointe
vers le document qui le remplace. Exiger le remplacement empêche une qualification
réelle de cesser silencieusement de compter.

**Conservation de l'historique.** Un document rejeté ou remplacé reste consultable
pour l'audit. `ON DELETE RESTRICT` sur `file_id` empêche la suppression d'un
document encore référencé.

Migration : `database/migrations/20261002_server_attestations.sql` (idempotente).

### server_locations
Historique des localisations des serveurs.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| server_id | UUID | Serveur concerné (FK servers) |
| city_id | UUID | Ville (FK cities) |
| area | VARCHAR(255) | Quartier/zone approximative |
| latitude | NUMERIC(10,8) | Latitude GPS |
| longitude | NUMERIC(11,8) | Longitude GPS |
| is_verified | BOOLEAN | Localisation confirmée par le serveur |
| verified_at | TIMESTAMP | Date de confirmation |
| is_current | BOOLEAN | Localisation actuelle |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

**Règles** :
- Un serveur peut avoir plusieurs anciennes localisations
- Une seule localisation `is_current = TRUE` par serveur (garanti par trigger)
- Les coordonnées GPS exactes sont considérées comme privées

### skills
Référentiel des compétences.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| name | VARCHAR(100) | Nom unique |
| description | TEXT | Description |
| created_at | TIMESTAMP | Date de création |

**Compétences pré-chargées** :
- Food
- Service à table
- Buffet
- Barman
- Bar
- Cocktail
- Mise en place
- Débarrassage
- Team Leader
- Maître d'hôtel
- Manager

### server_skills
Compétences des serveurs (many-to-many).

| Colonne | Type | Description |
|---------|------|-------------|
| server_id | UUID | Serveur (FK servers) |
| skill_id | UUID | Compétence (FK skills) |
| level | INTEGER | Niveau 1-10 |
| years_experience | INTEGER | Années d'expérience sur cette compétence |

**Clé primaire composite** : (server_id, skill_id)

### server_profile
Profil professionnel et scores.

| Colonne | Type | Description |
|---------|------|-------------|
| server_id | UUID | Serveur (FK servers) |
| speed_score | INTEGER | Rapidité 1-10 |
| punctuality_score | INTEGER | Ponctualité 1-10 |
| presentation_score | INTEGER | Présentation 1-10 |
| communication_score | INTEGER | Communication 1-10 |
| teamwork_score | INTEGER | Esprit d'équipe 1-10 |
| discipline_score | INTEGER | Discipline 1-10 |
| endurance_score | INTEGER | Endurance 1-10 |
| worker_type | worker_type | HARD_WORKER, BALANCED, SOFT_WORKER |

**IMPORTANT** : `worker_type` est indicatif. Le futur moteur de sélection ne doit pas s'y baser exclusivement.

### server_availability
Disponibilités des serveurs.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| server_id | UUID | Serveur (FK servers) |
| start_datetime | TIMESTAMP | Début de disponibilité |
| end_datetime | TIMESTAMP | Fin de disponibilité |
| status | availability_status | AVAILABLE, UNAVAILABLE, RESERVED |
| note | TEXT | Remarque |
| created_at | TIMESTAMP | Date de création |

**Contrainte** : `end_datetime > start_datetime`

### vehicles
Véhicules des serveurs.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| owner_server_id | UUID | Propriétaire (FK servers) |
| vehicle_type | vehicle_type | CAR, VAN, MOTORCYCLE, OTHER |
| brand | VARCHAR(100) | Marque |
| model | VARCHAR(100) | Modèle |
| seats_total | INTEGER | Nombre de places |
| can_transport_coworkers | BOOLEAN | Accepte le covoiturage |
| is_active | BOOLEAN | Véhicule actif |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

**IMPORTANT** : `can_transport_coworkers` est explicite. Posséder un véhicule n'implique pas automatiquement le covoiturage.

### vehicle_availability
Disponibilités des véhicules.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| vehicle_id | UUID | Véhicule (FK vehicles) |
| start_datetime | TIMESTAMP | Début |
| end_datetime | TIMESTAMP | Fin |
| available | BOOLEAN | Disponible |
| created_at | TIMESTAMP | Date de création |

**Contrainte** : `end_datetime > start_datetime`

### events
Événements.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| name | VARCHAR(255) | Nom de l'événement |
| client_name | VARCHAR(255) | Nom du client |
| city_id | UUID | Ville (FK cities) |
| address | TEXT | Adresse exacte |
| start_datetime | TIMESTAMP | Début |
| end_datetime | TIMESTAMP | Fin |
| guest_count | INTEGER | Nombre de convives |
| event_type | VARCHAR(100) | Type d'événement |
| alcohol_service | BOOLEAN | Service d'alcool |
| food_products_count | INTEGER | Nombre de produits alimentaires |
| priority | event_priority | NORMAL, PRIORITY, URGENT |
| is_urgent | BOOLEAN | Marqué comme urgent |
| urgent_created_at | TIMESTAMP | Date de marquage urgent |
| required_response_minutes | INTEGER | Délai de réponse requis (minutes) |
| status | event_status | PLANNED, STAFFING, CONFIRMED, IN_PROGRESS, COMPLETED, CANCELLED |
| notes | TEXT | Remarques |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

**Contrainte** : `end_datetime > start_datetime`

### event_requirements
Besoins en personnel d'un événement.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| event_id | UUID | Événement (FK events) |
| role_name | VARCHAR(100) | Rôle requis |
| quantity | INTEGER | Quantité nécessaire |
| required_gender | gender_type | Genre requis (optionnel) |
| minimum_experience | INTEGER | Expérience minimum (années) |
| minimum_skill_level | INTEGER | Niveau de compétence minimum 1-10 |
| notes | TEXT | Remarques |
| created_at | TIMESTAMP | Date de création |

**Flexibilité** : Les exigences sont paramétrables, pas codées en dur.

**`event_requirements` n'a pas de `skill_id`** (étape 24C-D-8B). `minimum_skill_level`
est donc un seuil numérique nu : aucune identité de compétence ne peut lui être
rattachée, et aucune n'est déduite de `role_name`. C'est la raison pour laquelle
`GET /api/events/{event_id}/print-data` expose ce seuil sous le nom explicite
`required_minimum_skill_level`, distinct des compétences réelles d'un serveur, qui
proviennent de `server_skills` et sont exposées sous `actual_skills`. Le champ
historique `assignments[].skill_level` du détail d'événement conserve son sens
d'origine (le minimum de l'exigence) et n'est pas renommé.

Aucune table n'est ajoutée ou modifiée par l'étape 24C-D-8B : le contrat
d'impression ne fait que lire `events`, `cities`, `event_requirements`,
`event_staff`, `servers`, `server_skills`, `skills`, `server_files`,
`server_attestations`, `transport_groups`, `transport_passengers` et `vehicles`.

### event_staff
Affectations de serveurs aux événements.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| event_id | UUID | Événement (FK events) |
| server_id | UUID | Serveur (FK servers) |
| role | VARCHAR(100) | Rôle attribué |
| assignment_status | assignment_status | PROPOSED, CONFIRMED, DECLINED, CANCELLED, COMPLETED |
| assigned_at | TIMESTAMP | Date d'affectation |
| confirmed_at | TIMESTAMP | Date de confirmation |

**Contrainte unique** : (event_id, server_id)

### evaluations
Évaluations des serveurs après événement.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| event_id | UUID | Événement (FK events) |
| server_id | UUID | Serveur (FK servers) |
| punctuality | INTEGER | Ponctualité 1-10 |
| work_quality | INTEGER | Qualité du travail 1-10 |
| presentation | INTEGER | Présentation 1-10 |
| teamwork | INTEGER | Esprit d'équipe 1-10 |
| client_relation | INTEGER | Relation client 1-10 |
| comment | TEXT | Commentaire |
| created_at | TIMESTAMP | Date de création |

**Contrainte unique** : (event_id, server_id)

### transport_groups
Groupes de transport pour les serveurs.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| event_id | UUID | Événement (FK events) |
| vehicle_id | UUID | Véhicule (FK vehicles) |
| driver_server_id | UUID | Conducteur (FK servers) |
| departure_latitude | NUMERIC(10,8) | Latitude départ |
| departure_longitude | NUMERIC(11,8) | Longitude départ |
| departure_location_label | VARCHAR(255) | Label lieu de départ |
| departure_time | TIMESTAMP | Heure de départ |
| destination_latitude | NUMERIC(10,8) | Latitude destination |
| destination_longitude | NUMERIC(11,8) | Longitude destination |
| destination_label | VARCHAR(255) | Label destination |
| estimated_distance_km | NUMERIC(6,2) | Distance estimée (km) |
| estimated_duration_minutes | INTEGER | Durée estimée (min) |
| status | transport_group_status | Statut du transport |
| created_at | TIMESTAMP | Date de création |

### transport_passengers
Passagers d'un groupe de transport.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| transport_group_id | UUID | Groupe de transport (FK transport_groups) |
| server_id | UUID | Serveur (FK servers) |
| pickup_latitude | NUMERIC(10,8) | Latitude du pickup |
| pickup_longitude | NUMERIC(11,8) | Longitude du pickup |
| pickup_location_label | VARCHAR(255) | Label lieu de pickup |
| pickup_order | INTEGER | Ordre de pickup (>=1) |
| pickup_status | pickup_status | Statut du pickup |
| created_at | TIMESTAMP | Date de création |

**Contrainte unique** : (transport_group_id, server_id)

### urgent_event_offers
Offres pour événements urgents.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| event_id | UUID | Événement urgent (FK events) |
| server_id | UUID | Serveur contacté (FK servers) |
| sent_at | TIMESTAMP | Date d'envoi |
| response_deadline | TIMESTAMP | Date limite de réponse |
| status | offer_status | PENDING, ACCEPTED, DECLINED, EXPIRED |
| responded_at | TIMESTAMP | Date de réponse |
| created_at | TIMESTAMP | Date de création |

**Contrainte unique** : (event_id, server_id)

### point_transactions
Historique des points attribués.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| server_id | UUID | Serveur (FK servers) |
| event_id | UUID | Événement (FK events, nullable) |
| points | INTEGER | Points (positif ou négatif) |
| transaction_type | transaction_type | EARNED, BONUS, PENALTY, ADJUSTMENT |
| reason | TEXT | Raison |
| created_by | UUID | Créateur (FK users, nullable) |
| created_at | TIMESTAMP | Date de création |

**IMPORTANT** : Historique complet des points. Ne pas stocker de total dans servers.

### monthly_rankings
Classements mensuels des serveurs.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| server_id | UUID | Serveur (FK servers) |
| year | INTEGER | Année (2000-2100) |
| month | INTEGER | Mois (1-12) |
| total_points | INTEGER | Total des points |
| rank | INTEGER | Classement |
| bonus_amount | NUMERIC(10,2) | Montant de la prime |
| status | ranking_status | CALCULATED, PAID, ARCHIVED |
| created_at | TIMESTAMP | Date de création |

**Contrainte unique** : (server_id, year, month)

### bonus_rules
Règles configurables des primes.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| name | VARCHAR(255) | Nom de la règle |
| min_points | INTEGER | Points minimum |
| max_points | INTEGER | Points maximum |
| rank_from | INTEGER | Classement minimum |
| rank_to | INTEGER | Classement maximum |
| bonus_amount | NUMERIC(10,2) | Montant de la prime |
| active | BOOLEAN | Règle active |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

## audit_log — journal d'audit

**Étape 24C-D-7.** Le journal enregistre les actions administratives. Il existe
une seule table, `audit_log`, alimentée par `app/services/audit_service.py` via
`log_audit_action(conn, actor_id, action, detail, target_id)`.

### Actions

`action` est une énumération `admin_audit_action`.

| Valeur | Signification |
|--------|---------------|
| `USER_CREATED` | Création d'un utilisateur |
| `USER_UPDATED` | Modification d'un utilisateur |
| `USER_DEACTIVATED` | Désactivation d'un utilisateur |
| `PROFILE_PHOTO_UPLOADED` | Ajout **ou remplacement** d'une photo de profil |
| `PROFILE_PHOTO_DELETED` | Suppression d'une photo de profil |
| `ATTESTATION_UPLOADED` | Dépôt d'un document d'attestation (toujours `PENDING`) |
| `ATTESTATION_VERIFIED` | Vérification explicite d'une attestation |
| `ATTESTATION_REJECTED` | Rejet d'une attestation |
| `ATTESTATION_SUPERSEDED` | Remplacement d'une attestation |

**Un seul évènement pour l'ajout et le remplacement d'une photo.** Il n'existe pas
d'action `REPLACED` : les deux opérations sont la même action perçue par
l'utilisateur, et la différence est portée par `detail->>'replaced'`
(`true` si une photo courante existait déjà). Aucun marqueur ne peut ainsi
diverger de l'autre.

Migration : `database/migrations/20261003_server_file_audit_actions.sql`
(idempotente, `ADD VALUE IF NOT EXISTS`).

### Acteur et cible

Une action porte sur un serveur n'est pas une action sur un utilisateur. Or
`target_user_id` est une clé étrangère vers `users(id)` : y écrire un
identifiant de serveur échouerait. **Pour les six actions serveur,
`target_user_id` reste donc `NULL`.**

| Élément | Rôle |
|---------|------|
| `actor_user_id` | Le MANAGER ou ADMIN authentifié qui a effectué l'action. Jamais lu dans le corps de la requête. |
| `detail->>'server_id'` | Le serveur concerné |
| `target_user_id` | `NULL` pour les actions serveur ; l'utilisateur concerné pour `USER_*` |

Il n'existe pas de colonne `target_server_id` : le serveur est déjà identifiable
dans le détail JSONB, et aucune nouvelle cible n'était nécessaire.

### Contenu du détail : métadonnées uniquement

Le détail est construit par **liste blanche explicite**, champ par champ. Il ne
contient jamais :

- les octets du document (`BYTEA`) ni l'objet fichier ;
- de coordonnées GPS ni aucune donnée de localisation ;
- de mot de passe, hash, jeton ou identifiant d'authentification ;
- d'URL publique, signée ou d pertain de stockage.

Champs journalisés pour une photo : `server_id`, `file_id`, `mime_type`,
`file_size`, `replaced`. Pour un dépôt d'attestation : `server_id`,
`attestation_id`, `file_id`, `qualification_name`, `mime_type`, `file_size`,
`status`. Pour une transition : `server_id`, `attestation_id`, `old_status`,
`new_status`, `qualification_name`, puis `verified_by` / `verified_at`,
`rejection_reason` ou `superseded_by_id` selon le cas.

La sanitisation appliquée à l'affichage du journal (redaction des clés sensibles,
profondeur bornée) est une protection **d'affichage** ; la garantie réelle est la
liste blanche côté serveur.

### Atomicité

L'écriture d'audit partage la **transaction de la mutation**. Une opération qui
échoue — donc une transaction annulée — ne laisse donc **aucun** enregistrement :
un journal ne peut pas annoncer la suppression d'une photo ou la vérification
d'une attestation qui n'ont pas eu lieu. La suppression de photo de profil a été
rendue transactionnelle pour cette raison ; elle utilisait auparavant un `UPDATE`
autocommité.

## Relations principales

```
cities ──< servers ──< server_locations
                    ├──< server_skills >── skills
                    ├──< server_profile
                    ├──< server_availability
                    ├──< vehicles ──< vehicle_availability
                    ├──< event_staff ──< events ──< event_requirements
                    ├──< evaluations
                    ├──< transport_passengers <── transport_groups
                    ├──< urgent_event_offers
                    └──< point_transactions
                            └──< monthly_rankings
```

## Indexes

Les indexes suivants optimisent les requêtes fréquentes :

- `servers.city_id`
- `server_locations.server_id`
- `server_locations.is_current`
- `server_availability.server_id`
- `server_availability(start_datetime, end_datetime)`
- `vehicles.owner_server_id`
- `vehicle_availability.vehicle_id`
- `events.city_id`
- `events.start_datetime`
- `events.status`
- `events.is_urgent`
- `event_requirements.event_id`
- `event_staff.event_id`
- `event_staff.server_id`
- `transport_groups.event_id`
- `urgent_event_offers.event_id`
- `urgent_event_offers.server_id`
- `point_transactions.server_id`
- `monthly_rankings(year, month)`

## Triggers

- `update_updated_at_column` : Met à jour automatiquement le champ `updated_at` sur plusieurs tables
- `enforce_single_current_location` : Garantit qu'un serveur ne peut avoir qu'une seule localisation actuelle

## Sécurité et vie privée

- Les coordonnées GPS exactes (`latitude`, `longitude`) sont stockées dans `server_locations` mais **ne doivent jamais être exposées publiquement**
- L'adresse exacte du domicile n'est pas stockée dans `servers`
- Le futur système devra contrôler les permissions d'accès aux données sensibles

## Exécution

```bash
# Créer la base de données
createdb le_seizieme

# Appliquer le schéma
psql -U postgres -d le_seizieme -f schema.sql

# Insérer les données de référence
psql -U postgres -d le_seizieme -f seed.sql
```
