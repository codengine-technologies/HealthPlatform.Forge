# todo-task-301.md — Reprise de l'historique d'audit vers la base commune, à débit borné, puis retrait de la table par praticien

**Repos**: api-mail
**Dependencies**: **task-299** (annuaire — sans lui, les bases à reprendre ne sont pas
énumérables), **task-300** (table commune, partitionnement, RLS)
**Epic**: E016
**Single frontend**: true
**Priorité**: **2** — ferme le chantier. Sans elle, chaque praticien traîne indéfiniment une
table d'audit résiduelle et le chemin de lecture double de task-300 reste en place.

## Objective

Reprendre les traces d'audit **déjà écrites** dans les bases praticien vers la table commune,
**sans tempête de connexions**, puis retirer la table par tenant et le chemin de lecture double
introduit par task-300.

### La contrainte qui gouverne toute l'US

La reprise parcourt le parc entier : c'est **exactement la forme d'opération qui a mis Postgres
à genoux trois fois le 2026-09-11** (rejeu du tampon : 2 500 backends en 3 minutes, 27 575
refus `53300`, VM Docker figée 45 minutes). La leçon de task-298 s'applique intégralement ici :
**une opération qui touche les 1000 bases doit être lente et bornée, jamais rapide et large.**

Donc : concurrence plafonnée et configurable (défaut **4** bases simultanées), lots bornés,
reprise possible après interruption, et **arrêt automatique** si Postgres approche sa limite de
connexions. Une reprise qui prend une nuit est un succès ; une reprise qui sature le serveur
est un échec, même si elle est plus rapide.

### Déroulé

1. **Énumérer** les messageries depuis l'annuaire (task-299) — l'opération n'était pas
   réalisable avant, c'est ce que l'annuaire débloque.
2. Pour chaque base, **copier par lots** les traces antérieures à l'instant de bascule vers la
   table commune, en renseignant le `TenantId`, **idempotent** (une trace déjà reprise n'est
   jamais dupliquée — clé d'identité conservée).
3. **Vérifier** : nombre de traces reprises == nombre de traces source, par messagerie. Toute
   divergence est un échec bloquant pour cette messagerie, journalisé, sans arrêter les autres.
4. Marquer la messagerie **reprise** dans l'annuaire ; l'écran d'audit cesse alors d'interroger
   la source héritée pour ce praticien.
5. Quand **toutes** les messageries sont reprises et vérifiées : retirer le chemin de lecture
   double, puis supprimer la table d'audit des bases praticien (migration par tenant).

L'étape 5 est **séparée dans le temps** de l'étape 4 et conditionnée à une validation humaine
explicite : on ne supprime pas une source de traçabilité PGSSI-S le jour même de sa copie.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Commande de reprise déclenchable à la demande (pas de cron : `api-mail` n'a pas
      d'ordonnanceur), reprenable après interruption sans reprendre depuis le début
- [ ] Test unitaire : la reprise ne dépasse **jamais** `Backfill:MaxConcurrentDatabases`
      (défaut 4) bases simultanées, quel que soit le nombre de messageries dans l'annuaire
      (compteur de concurrence observé)
- [ ] Test unitaire : **idempotence** — rejouer la reprise sur une messagerie déjà reprise
      n'insère aucune ligne et ne lève pas
- [ ] Test unitaire : **garde-fou de saturation** — au-delà d'un seuil de connexions Postgres
      configurable, la reprise se met en pause au lieu de continuer (fixture simulant la
      saturation)
- [ ] Test unitaire : une messagerie en échec (base injoignable, divergence de comptage)
      **n'interrompt pas** la reprise des autres ; elle est journalisée et laissée non marquée
- [ ] Test d'intégration : après reprise d'une messagerie, l'écran d'audit du praticien rend
      **exactement le même contenu** qu'avant la reprise — même nombre, même ordre, aucun doublon
- [ ] Test : la vérification de comptage par messagerie échoue **bruyamment** si une seule trace
      manque (test par retrait délibéré d'une ligne)
- [ ] Migration par tenant supprimant la table d'audit héritée, appliquée **uniquement** aux
      messageries marquées reprises et vérifiées
- [ ] Retrait du chemin de lecture double de task-300 et de la configuration devenue morte
      (`Audit:DrainParallelism`, plafond de drain côté audit) — le code ne garde pas deux
      architectures en parallèle
- [ ] Aucune donnée de santé en clair dans les logs de reprise (nombre de traces, nom de base,
      identifiant de tenant : oui ; contenu de trace : jamais)
- [ ] Documentation : runbook `Api/Mail/docs/runbook-reprise-audit.md` — comment lancer,
      comment suivre l'avancement, comment reprendre après incident, comment **vérifier avant
      de supprimer**

## Manual Test Plan

- **Pré-requis** : task-299 et task-300 déployées ; au moins deux praticiens de test disposant
  de traces antérieures à la bascule.
- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`, puis déclencher la reprise
  selon le runbook.
- **Ce que l'humain doit voir** :
  1. Pendant la reprise :
     `docker exec postgres-pgvector psql -U postgres -c "select application_name, count(*) from pg_stat_activity group by 1"`
     → le chemin de reprise reste **≤ 4 connexions**, et `docker logs --since 5m postgres-pgvector`
     ne contient **aucun** « too many clients ».
  2. Après reprise d'un praticien : son écran d'audit affiche le **même historique qu'avant**
     (comparer un export avant / après — même nombre de lignes, même ordre).
  3. Relancer la reprise une seconde fois → **aucune ligne insérée**, aucune erreur.
  4. Couper une base praticien pendant la reprise → cette messagerie est signalée en échec, les
     autres se terminent normalement.
  5. **Avant toute suppression** : vérifier messagerie par messagerie que le comptage source ==
     comptage cible. C'est la porte de validation humaine de l'étape 5.
- **Données de test** : praticiens synthétiques du banc, aucune donnée réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — continuité de la traçabilité
- **Exigences DSR honorées** : non applicable
- **INS** : les traces reprises portent `PatientIns` — contenu **inchangé**, simple déplacement
  physique, même finalité, même rétention
- **Authentification PS** : inchangée
- **Habilitations** : la reprise est une opération d'exploitation, pas un accès praticien ;
  elle n'ouvre **aucun** nouveau chemin de lecture
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **point de vigilance central** — l'US déplace puis **supprime** une source
  de traçabilité. D'où l'exigence de vérification par comptage, la séparation dans le temps
  entre copie et suppression, et la validation humaine explicite avant l'étape 5. Aucune trace
  ne doit disparaître : c'est le critère d'acceptation de l'US
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — déplacement interne au même environnement HDS, aucun flux sortant
- **AIPD / impact RGPD** : couverte par la mise à jour de task-300 ; cette US en est l'exécution
