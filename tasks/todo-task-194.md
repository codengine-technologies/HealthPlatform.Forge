# todo-task-194.md — Chaque page de dossier balaye toute la table des mails ; historique patient non paginé

**Repos**: api-mail
**Dependencies**: —
**Epic**: E011
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe accès données).
> Rattaché à **E011 (performance api-mail)** et non à E009 : le défaut est de nature
> performance, pas fonctionnelle.

## Objective

Supprimer deux motifs d'accès aux données dont le coût croît avec la **taille totale
de la boîte** au lieu de la taille de ce qui est demandé. Sur une boîte MSSanté
réelle, la messagerie devient lente au point d'être inutilisable, et la
consommation mémoire du serveur suit le volume de la boîte, non celui de la page.

**US backend-only (justification)** : requêtes côté serveur, aucun contrat modifié.

### Preuve (état actuel du code)

**1. Comptage de fils de discussion — deux balayages complets par page**
`src/Infrastructure/Repository/MailRepository.cs:3171-3181` (et le doublon
`:1167-1176`) émet deux chargements **sans aucun filtre** : tous les `MessageId` de
la base, puis toutes les lignes `(MessageId, InReplyTo, References)` dont l'un des
champs de référence est non vide — sans filtre de dossier, sans pagination, sans
`AsNoTracking`. Il imbrique ensuite
`allMailsWithReferences.Count(m => … m.References.Contains(rootId))` dans une boucle
sur les racines de la page. Le helper `BuildThreadCountsByRoot` (`:1199`) prend un
`IReadOnlyCollection<dynamic>` : **chaque** accès `m.InReplyTo` / `m.References`
passe donc par le liant dynamique du runtime.

Cet enrichissement s'exécute sur **chaque** page de **chaque** listage de dossier
(`src/Application/Services/Implementation/OnlineMailDataProvider.cs:83-89`).
Sur une boîte de 50 000 messages : ~50 000 chaînes d'identifiants plus ~50 000
lignes à trois champs matérialisées par page, puis 50 racines × 50 000 lignes =
**2,5 millions** de recherches de sous-chaîne à répartition dynamique — par page,
par praticien, à chaque rafraîchissement.

**2. Historique patient sans pagination, avec une requête par document**
`src/Infrastructure/Repository/PatientRepository.cs:201-256` : aucun `Take`, aucune
pagination — l'intégralité de l'historique documentaire du patient est retournée.
Puis `EnrichBiologyAndAttachmentsAsync` (`:338-358`) regroupe correctement la
biologie mais émet **une requête de pièces jointes par document**, dans un
`foreach`. À noter aussi `GetMailsByInsAsync` (`:361-365`) qui délègue avec
`pageSize = int.MaxValue`.

Un patient chronique suivi plusieurs années cumule des centaines de CDA : ouvrir son
dossier matérialise tous les documents avec leur corps complet, puis enchaîne
autant d'allers-retours qu'il y a de documents. Sur une connexion lente, le délai
client peut expirer — le dossier ne s'ouvre jamais.

### Contenu attendu

1. **Comptage de fils borné** : calculer les compteurs pour les seules racines de la
   page demandée, en SQL (agrégation côté base), sans matérialiser la table. Filtrer
   par dossier quand la sémantique le permet.
2. **Sortir de `dynamic`** : types explicites sur ce chemin — le liant dynamique
   coûte cher et prive de toute vérification.
3. **Historique patient paginé** : pagination effective sur les documents et les
   mails du patient, et chargement des pièces jointes **par lot** (une requête pour
   l'ensemble de la page, pas une par document). Traiter aussi
   `pageSize = int.MaxValue`.
4. **Mesurer avant / après** : le banc de charge des tasks 173/174 existe
   précisément pour cela. Chiffrer le gain sur une boîte représentative plutôt que
   d'affirmer une amélioration.
5. **Ne pas régresser fonctionnellement** : les compteurs de fils et le contenu du
   dossier patient doivent rester **identiques** — seul le coût change. C'est la
   condition pour que ce soit une task de performance et non un changement de
   comportement.

### Hors scope

- L'identité des mails → task-179 (mais s'aligner dessus si elle est livrée avant).
- La pertinence de la recherche → task-192.
- Toute modification du contrat d'API (la pagination doit s'appuyer sur les
  paramètres existants ; si un nouveau paramètre s'avère nécessaire, le documenter et
  prévoir un défaut compatible).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test : le comptage de fils ne charge plus l'intégralité de la table — vérifié
      par assertion sur le SQL émis ou sur le nombre de lignes matérialisées (ce test
      doit échouer sur le code actuel — le vérifier explicitement)
- [ ] Test de non-régression fonctionnelle : les compteurs de fils retournés sont
      **identiques** à ceux du code actuel sur un jeu de données de référence
      (messages avec `In-Reply-To` et `References` variés)
- [ ] Test : l'historique documentaire du patient est paginé, et les pièces jointes
      sont chargées par lot (nombre de requêtes indépendant du nombre de documents)
- [ ] Test de non-régression fonctionnelle : le contenu du dossier patient (mêmes
      documents, même ordre) est inchangé
- [ ] Plus aucun `dynamic` sur le chemin de comptage de fils
- [ ] **Mesures chiffrées avant / après** consignées dans la task, obtenues sur le
      banc de charge (tasks 173/174) avec une boîte représentative : latence p50/p95
      du listage de dossier, et temps d'ouverture d'un dossier patient fourni
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Préparer le banc : profil de charge des tasks 173/174 avec une boîte fournie
   (idéalement ≥ 10 000 messages ; à défaut, documenter le volume atteint) et un
   patient de test porteur de nombreux documents.
2. **Mesure avant** : lancer le backend, mesurer la latence d'un listage de dossier
   (scénario `read` du banc, p50/p95) et chronométrer l'ouverture du dossier patient
   fourni. Consigner les chiffres.
3. Appliquer le correctif, relancer les **mêmes** mesures. **Attendu** : baisse
   nette et chiffrée, et une latence qui ne croît plus avec la taille totale de la
   boîte.
4. **Non-régression fonctionnelle** : comparer côte à côte, avant et après, les
   compteurs de fils affichés sur plusieurs pages d'un dossier à discussions —
   valeurs identiques.
5. Ouvrir le dossier du patient fourni : mêmes documents, même ordre, mêmes pièces
   jointes qu'avant, mais ouverture rapide et sans expiration de délai.
6. Observer la mémoire du serveur pendant un parcours de plusieurs pages : elle ne
   doit plus suivre le volume total de la boîte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — sujet de performance ; contribue
  indirectement à l'utilisabilité du LPS sur le volet MSSanté
- **Exigences DSR honorées** : non applicable — aucune exigence fonctionnelle
  nouvelle
- **INS** : non applicable — aucune règle d'identité modifiée
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — le périmètre des données lues doit rester
  strictement identique (attention à ne pas élargir un filtre en optimisant)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — ne pas réduire la journalisation existante en
  optimisant les requêtes
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement, aucun changement de
  périmètre de données.
