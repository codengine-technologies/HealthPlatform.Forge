# Laboratoire CPU de l'analyse des mails — 2026-10-31 / 2026-11-01

> Suite de la [phase 0](api-mail-loadtest-phase0-cout-cpu-enrichissement-20261031.md). Mode laboratoire demandé
> par l'humain : itérer une solution à la fois, tirer 16 médecins pendant 8 min après chaque changement, garder
> seulement ce qui apporte un gain mesuré, sans régression.

## Résultat

| Indicateur | Initial (moyenne B0, B0b, B0c) | Final (moyenne E4b, E4br) | Écart |
|---|---|---|---|
| **CPU de l'API par mail** | 99,9 ms | **65,9 ms** | **−34,0 %** |
| **Débit** (16 médecins) | 46,4 mails/s | **56,1 mails/s** | **+21 %** |
| CPU du poste par mail | 394 ms | 262 ms | −33 % |
| CPU de Postgres par mail | 31,5 ms | 23,2 ms | −26 % |
| Durée serveur d'un mail | 267 ms | 216 ms | −19 % |
| Lot de 10 mails, p50 / p95 | 3,45 s / 4,64 s | 2,87 s / 3,79 s | −17 % / −18 % |
| Allers-retours SQL par mail | 46,1 | 43,0 | −7 % |
| Collectes GC gen2 / 1 000 mails | 35,9 | 25,8 | −28 % |
| Journaux Information par mail | 30,5 | 2,4 | −92 % |
| Erreurs, seuils k6 en échec | 0, 0 | 0, 0 | — |

- **Bruit mesuré** entre trois essais identiques : ±1,5 % sur le CPU de l'API (l'indicateur de décision), ±4 % sur le
  CPU du poste, ±10 % sur celui de Postgres.
- **Debug ou Release** : A/B à vectorisation coupée dans les deux jambes (D0 51,7 / R0 51,0 ms par mail), **−1,4 %,
  dans le bruit**. Le CPU se dépense dans des bibliothèques déjà compilées en Release (PdfPig, AngleSharp, EF,
  Npgsql, TLS). Les chiffres du banc valent pour la production ; l'hypothèse inverse de la phase 0 est infirmée.

## Protocole

- **Branches** : `lab/cpu-enrichissement` sur `api-mail` et sur `interop-cda`, **non poussées**. `api-mail`
  consomme `interop-cda` depuis un flux NuGet local (`109.0.1-lab.N`), y compris pour les références.
- **Banc** :
  - AppHost `https-load-test`, 5 réplicas, banc mail cluster, latence 96 ms, tireur k6bench ;
  - tout OpenAI, étiquetage coupé, vectorisation active ;
  - AppHost redémarrée à froid avant chaque essai.
- **Essai** :
  - `reset-state.sh --keep-analysed 462 --users 300` ;
  - `enrich` à 16 médecins, boîtes 1 à 300, lots de 10, 8 min ;
  - fenêtre de mesure propre [t+75 s, t+435 s], sans profileur.
- **Non-régression** :
  1. tests unitaires et d'intégration à chaque changement, puis suite complète à la fin ;
  2. **oracle par empreinte** : ~1 600 à 1 800 mails analysés par essai (boîtes 1 à 20), comparés par composant
     (mail, corps, HTML, métadonnées et texte des documents, biologie, pièces jointes, destinataires, étiquettes,
     patients, doublons, embeddings) ;
  3. seuils k6, erreurs et avertissements Seq par mail.

## Itérations

| # | Changement | CPU API (ms/mail) | Gain propre | Décision |
|---|---|---|---|---|
| E2 | `CdaValidator` : une seule lecture et analyse du CDA (le `XmlSchemaSet` chargé pour chaque document n'était jamais utilisé ; le document était relu 3 fois) | 94,5 | −5,4 % | **gardé** |
| E3 | Ressources XSLT servies depuis la mémoire | 94,1 | 0 % | **gardé pour l'exactitude** : corrige une perte de données (voir constats) |
| E1 | Journaux de suivi d'étape émis pour chaque mail : Information → Debug ; Polly en Warning | 90,8 | −3,5 % | **gardé** |
| E4 | Relais SSE : en-tête + charge brute (format changé) | 97,0 | **+6,8 %** | **rejeté** (régression : tableaux de la taille du mail sur le tas des gros objets, GC gen2 ×2,3) |
| E5 | Assainissement HTML (AngleSharp) sans observateur d'attributs : plus d'URL construite pour chaque `src` d'iframe ou d'image (PDF en base64) | 86,9 | −4,3 % | **gardé** |
| E7a | Écritures ciblées (`ExecuteUpdate`) au lieu de lire la ligne entière : embedding du contenu, embedding du document, lien contact | 85,1 | −2,1 % (Postgres −15 %) | **gardé** |
| E7b | La vectorisation lit les documents sans leur HTML | 84,0 | −1,3 % (bruit) | **rejeté** |
| **E6** | **Archive IHE-XDM entièrement en mémoire** : plus de zip ni d'extraction sur disque ; mêmes bornes, mêmes contrôles de chemin, même classement des échecs | 72,8 / 71,4 | **−14,5 %** (poste −31 %) | **gardé** |
| E8 | Une extraction de texte PDF à la fois par processus (verrou global de PdfPig, `OperatorToken.Lock`, toujours là en 0.1.16) | 70,5 | −2,2 % | **gardé** |
| **E4b** | Relais SSE, format **inchangé** : la réception ne lit que l'en-tête, la charge (le `MailDto` entier) n'est décodée que si un abonné local la demande | 65,7 / 66,1 | **−6,8 %** (GC gen2 −20 %) | **gardé** |
| E9 | Moins de copies sur le tas des gros objets (HTML assaini, enveloppe SSE en tampon du pool) | 65,7 | 0 % | **rejeté** |

Essais de contrôle :
- **F1** (état final) : 64,3 ms, légèrement optimiste (crédit OpenAI épuisé à la fin de la fenêtre).
- **F2** : VOID, aucun embedding.
- **D0 / R0** : A/B Debug / Release ci-dessus.

## Non-régression

- **Oracle** : à chaque essai, différences limitées au bruit préexistant identifié (indicateurs de doublon, voir
  constats). Aucune différence de contenu, de documents, de biologie, de pièces jointes ni de patients.
- **Tests ajoutés**, chacun vu rouge par mutation puis vert :

| Changement | Test ajouté | Mutation qui le fait rougir |
|---|---|---|
| E3 | `InMemoryXsltResolverTests` (interop-cda) | lecture disque réinjectée |
| E4b | `SseBackplaneEnvelopeTests` | charge décodée immédiatement |
| E5 | `HtmlBodySanitizerParsingTests` | rouge naturel : un premier essai laissait l'observateur |
| E6 | `XdmLoadInMemoryTests` (interop-cda) et `CdaParsingInMemoryEquivalenceTests`, dont le cas avec PDF associé | la voie mémoire perd les PDF associés |
| E7a | `MedicalDocumentRepositoryIntegrationTests`, sur Postgres | l'`UPDATE` touche une autre colonne |
| E8 | `PdfTextExtractionConcurrencyTests` (interop-cda) | — |

- **Suite complète** (fin de laboratoire, build Debug) :
  - api-mail : domaine 202, infrastructure 699, API 1 315, application 3 956 tests, tous verts ;
  - intégration : 1 089 verts et 4 rouges :
    - 3 tests « du jour », rouges connus de la fenêtre 00:00–02:00 (date UTC), rejoués à 02:05 sur le même build : 3/3 verts ;
    - 1 test dont l'archive illisible journalisait, sur la voie mémoire, un message différent de celui exempté.
      Corrigé : la voie mémoire reprend les messages de la voie disque (`interop-cda` `109.0.1-lab.6`). Le comportement
      était déjà correct ;
  - interop-cda : 517 verts (6 ignorés : jeux de données locaux absents).
- **Trou du filet comblé** : aucune des 7 archives de `Resources/cda-samples/` ne porte de PDF associé au CDA. Une
  voie qui perdait ces PDF ne faisait rougir aucun test. Le cas est désormais fabriqué à partir d'une archive réelle.

## Constats faits en route

1. **Défaut produit corrigé par E3** :
   - au démarrage d'une réplique, les premières transformations CDA → HTML concurrentes échouaient (« The process
     cannot access the file 'cda_asip.xsl' ») ;
   - le document était alors **stocké sans corps ni HTML, et le mail marqué analysé**, soit une perte définitive ;
   - 4 à 5 documents par démarrage à froid au banc, **0** avec E3 ;
   - cause : chaque processus effaçait et réécrivait `%TEMP%/cda_xslt_html`, et la XSLT relisait `cda_l10n.xml` sur
     disque à chaque transformation.
2. **Détection de doublon / remplacement non déterministe** : pour une paire de mails portant le même document (même
   `DocumentId` et version, UID voisins, environ 60 s d'écart), `DuplicateOfId` et `SupersededByDocumentId` varient
   d'un essai à l'autre. Préexistant, hors périmètre ; à instruire.
3. **`[AiCall]` reste en Information** : la trace par appel IA est une exigence (task-385). C'est le plus gros volume
   de journaux restant (~2 par mail) ; la rétrograder relève d'une décision humaine.
4. **Cache de requêtes EF** : hypothèse d'un fournisseur EF par base **infirmée** (173 succès par seconde, 0 échec).
   Les options EF sont construites sans fabrique de journalisation : les avertissements d'EF ne sont visibles nulle
   part.
5. **Audit en lots minuscules** : ~1 trace par lot sous charge. Un délai de regroupement réduirait les instructions,
   au prix d'un délai de persistance ; c'est un choix de politique, non tenté.
6. **Crédit OpenAI épuisé** le 2026-10-31 à 23:44:51 (`429 insufficient_quota`). Des appels OpenAI en échec coûtent
   **plus** de CPU que des appels réussis (69,6 contre 65,9 ms par mail).

## Pistes non retenues (sous le seuil de mesure, ou décision produit)

| Piste | Raison |
|---|---|
| Fusionner les 4 analyses HtmlAgilityPack de la conversion HTML → texte | ~1 % estimé, risque sur le texte produit |
| Un seul appel d'embedding par mail (mail + document) | ~1 à 1,5 % de CPU, mais **divise par 2 les requêtes OpenAI facturées** ; change la sémantique d'échec et la métrologie par type de contenu |
| Contacts patient/praticien traités dans le consommateur au lieu de 2 messages de bus par mail | ~3 % estimé ; change les reprises sur échec |
| Ne publier sur le relais SSE que si un abonné existe quelque part, ou alléger l'évènement (identifiants au lieu du `MailDto` entier) | grand gain, croissant avec le nombre de réplicas ; **contrat client ou registre de présence** à décider |
| Cache de la variable d'environnement de provisionnement | 0,7 %, non mesurable |

## Ce qui reste (profil de l'état E6, en part du CPU managé utile)

TLS (IMAP, Redis, OpenAI) 10 %, assainissement HTML 6,8 %, Npgsql 5 %, PdfPig ~5 % (hors attente), validation CDA
4,8 %, XSLT 3,7 %, RabbitMQ 3 %, conversion HTML → texte ~3,7 %. Aucun de ces postes n'a de remède connu au-dessus
du seuil de mesure sans décision produit.

## Pour passer en production

- Les branches sont **locales, non poussées**. `api-mail` pointe sur un flux NuGet local : à remplacer par une
  publication normale d'`interop-cda` (dépôt porteur de contrat, NuGet publié par sa CI).
- **Prototype E6 à finir** avant production :
  - le registre en mémoire des fichiers de travail est global au processus : une fuite si un lot n'est jamais libéré
    (le disque avait son balayage au démarrage) ;
  - le passage par des « chemins » factices doit devenir un type porteur des octets ;
  - le répertoire de travail et son balayage deviennent inutiles.
- Découpage retenu : **une seule task `/po`**, sur `interop-cda` et `api-mail`, qui porte E3, E2, E8, E6, E1, E5,
  E7a et E4b. Un découpage en 7 tasks (une par levier) avait d'abord été proposé, puis écarté le 2026-11-01 :
  - le gain de chaque levier est déjà mesuré au laboratoire, il n'y a rien à re-mesurer task par task ;
  - un cycle de forge est long, et 7 cycles enchaînés retarderaient aussi le correctif E3 ;
  - le diff tient dans la limite d'une PR par dépôt : 14 fichiers sur `interop-cda`, et environ 31 fichiers de code
    et de tests sur `api-mail`, hors `packages.lock.json` ;
  - un seul paquet `interop-cda` à publier, une seule montée de version côté `api-mail`.
  - Le prix : une PR plus grosse à relire au HAG, et un échec à une étape bloque tous les leviers à la fois.
  - Un tir de contrôle 16 médecins × 8 min après merge confirme le gain d'ensemble, crédit OpenAI rechargé.

Sources :
- journal détaillé, oracle et pilotes : scratchpad de la session (`labo/`) ;
- fichiers bruts : `Api/Mail/tests/loadtest-k6/reports/2026-10-31/` (k6, observe, pg_stat_statements) ;
- Prometheus du banc.

## Tir de contrôle après merge — C1, `develop` @ `b2b0b5e7` (2026-11-01)

Le code de production (task-419, PR interop-cda #13 et api-mail #334, mergées) est comparé à l'état final du
laboratoire. **Crédit OpenAI toujours épuisé** (`credit_balance_exhausted`) : le tir est fait **vectorisation
coupée**, et sa référence est donc **D0** (état final du laboratoire, Debug, vectorisation coupée). Même protocole
(16 médecins, 8 min, fenêtre [t+75 s, t+435 s], AppHost redémarrée à froid, Debug), étiquetage coupé.

| Indicateur | D0 (labo final) | C1 (develop) | Écart |
|---|---|---|---|
| CPU de l'API par mail | 51,7 ms | 50,6 ms | −2,1 % |
| Débit | 57,6 mails/s | 56,6 mails/s | −1,7 % |
| CPU du poste par mail | 225 ms | 217 ms | −3,4 % |
| CPU de Postgres par mail | 15,4 ms | 16,0 ms | +4,0 % (bruit ±10 %) |
| Lot de 10 mails, p50 / p95 | 2,74 s / 3,66 s | 2,78 s / 3,76 s | +1,5 % / +2,7 % |
| Erreurs, seuils k6 en échec | 0, 0 | 0, 0 | — |
| **Empreinte de non-régression** | — | **identique** sur 1 800 mails communs | — |

**Verdict** : le code mergé reproduit l'état final du laboratoire, à l'intérieur du bruit. La finition de l'archive
en mémoire (lot porteur des octets au lieu du registre statique) n'a rien coûté.

**Pic mémoire par réplica** (`dotnet_process_memory_working_set_bytes`, maximum sur la fenêtre) :

| Essai | Réplica le plus chargé | Moyenne des 5 réplicas |
|---|---|---|
| B0 (initial, archives sur disque) | 2 764 Mio | 2 132 Mio |
| C1 (develop, archives en mémoire) | 2 560 Mio | 1 773 Mio |

Tenir les archives en mémoire n'alourdit pas les réplicas : leur pic baisse, avec moins d'allocations du reste de
la chaîne.

**Reste à faire** : le même tir **vectorisation active**, à comparer à B0, quand le crédit OpenAI sera rechargé. Il
chiffrera le gain final en conditions de production.
