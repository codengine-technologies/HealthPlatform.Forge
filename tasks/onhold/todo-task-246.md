# todo-task-246.md — Le banc n'exerce pas la voie que le médecin emprunte réellement

> ⏸️ **ON HOLD (décision humaine 2026-08-09)** — retirée du backlog actif. Le banc
> ne sait pas lire un flux SSE (k6 v1.4.2 : `k6/experimental/sse` retiré en v1.x, ni
> `go` ni `xk6` installés), donc le critère « déclenchement → évènement reçu » n'est
> pas implémentable en l'état — analyse complète dans `questions/answered/task-246.md`.
>
> **Et surtout, ce n'est pas le bon moment** : task-244 et task-245 viennent de changer
> la façon dont un tir est jugé, sans qu'aucun tir 500 ne les ait encore exercées.
> Changer en plus la **définition du parcours mesuré** déplacerait la référence une
> troisième fois avant d'en avoir fixé une seule.
>
> **Pour réactiver** : merger 244/245, tirer un 500, lire les chiffres — puis
> redéplacer ce fichier dans `tasks/` et `/start 246`. Envisager alors de couper en
> **246a** (coût résident des connexions : ne demande aucune extension k6, ne casse
> pas la comparabilité) et **246b** (latence perçue : exige un k6 recompilé).

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-244** (chauffe) et **task-245** (instrument
d'enrichissement) — celle-ci change la **définition du parcours mesuré**, elle
doit donc venir après elles.
**Priorité**: **2** — pas un incident, mais un **angle mort de mesure** : à 500
praticiens, une famille entière de coût résident n'est éprouvée nulle part.

## Objective

Que le banc mesure l'attente **telle que le médecin la vit** : déclenchement de
l'enrichissement, puis attente d'un **évènement poussé** — et non la durée d'un
appel synchrone que l'application mobile n'utilise pas.

## Ce qui est établi

Le backend expose **deux voies**, et le banc n'en exerce qu'une :

| | Production (client-mobile) | Banc de charge aujourd'hui |
|---|---|---|
| Déclenchement | `POST .../emails/enrich/async` — mise en file, retour immédiat | `POST .../emails/enrich/sync` — la requête bloque |
| Attente | connexion **SSE** longue durée `GET /api/v1/mail/events/stream`, poussée par `MailEnrichmentNotifier` | la durée de la requête HTTP |
| Fin | évènement reçu, la vue se rafraîchit | code 200 |

Vérifié le 2026-08-09 : le harnais k6 ne contient **aucune** connexion
`events/stream`, aucun `EventSource`.

**Trois choses ne sont donc mesurées nulle part :**

1. **Les connexions SSE longue durée** — une par praticien connecté, maintenue
   ouverte, multipliée par les réplicas. C'est un **coût résident**, de la même
   famille que les sessions IMAP et les backends Postgres, c'est-à-dire de la
   famille qui **plafonne une montée en population**. À 500 médecins, ce sont
   500 connexions persistantes que rien n'a éprouvées.
2. **La file du processeur d'arrière-plan** (`IBackgroundTaskQueue`,
   `BackgroundEnrichmentProcessor`) : sa concurrence et sa profondeur sous charge.
3. **La latence perçue** — déclenchement jusqu'à évènement — qui inclut l'attente
   derrière les autres praticiens.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que la voie synchrone majore la voie réelle.** Elle peut tout
  aussi bien la **minorer** : le chemin synchrone s'exécute dans le contexte de la
  requête, sans passer par la file. Les deux voies se comparent, elles ne se
  déduisent pas l'une de l'autre.
- **Ne pas présumer que 500 connexions SSE sont gratuites.** C'est précisément ce
  qu'il faut mesurer : mémoire, threads, sockets, sessions par réplica.

## Definition of Done

- [ ] Le scénario `journey` ouvre **et maintient** une connexion SSE par médecin
      pendant tout le tir
- [ ] L'enrichissement du parcours passe par la voie **async**
- [ ] Une étape de la grille SLO mesure le délai **déclenchement → évènement reçu**
- [ ] Le nombre de connexions SSE actives rejoint la table des **coûts résidents
      contre N**, au même titre que les sessions IMAP et les backends
- [ ] La **rupture de comparabilité** avec l'historique de l'EPIC est écrite dans
      `reports/INDEX.md` : le parcours mesuré change, les tirs antérieurs ne sont
      plus comparables sur cette étape
- [ ] Un tir 500 distant termine avec les 500 connexions SSE tenues

## Manual Test Plan

- Tir `journey` court ; pendant le tir, compter les connexions actives sur
  `/mail/events/stream` côté serveur et vérifier qu'elles valent la population
- Vérifier que l'étape « attente de fin d'enrichissement » a des échantillons
- Comparer, sur un même palier, la voie sync (ancienne) et la voie async + SSE :
  l'écart est le résultat, dans un sens comme dans l'autre

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de mesure
- **Exigences DSR honorées** : aucune
- **Authentification PS** : ⚠️ le flux SSE est **authentifié** — l'email est résolu
  depuis les claims du jeton, **jamais** depuis `?email=`. Le harnais doit
  emprunter le même chemin (un jeton par identité), sans quoi il mesurerait une
  voie qui n'existe pas en production.
- **Habilitations** : chaque médecin ne doit recevoir que **ses** évènements — le
  tir doit le vérifier. Un évènement reçu pour le compte d'un autre praticien est
  un défaut de **confidentialité** et primerait sur toute conclusion de performance.
- **INS / Consentement / Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — données synthétiques
- **Hébergement HDS** : sans objet (banc de test)
- **AIPD / impact RGPD** : inchangé
