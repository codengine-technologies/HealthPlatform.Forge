# questions/task-246.md — le banc ne peut pas observer un évènement SSE avec le k6 installé

**Task** : task-246 — « Le banc n'exerce pas la voie que le médecin emprunte réellement »
**État** : laissée en `todo-*`. **Aucune branche créée**, aucun code écrit — le
blocage est en amont de l'implémentation.
**Date** : 2026-08-09
**Décision demandée** : oui, et elle porte sur le **binaire du banc**, pas sur le code.

---

## Le blocage, en une phrase

**Le k6 installé ne sait pas lire un flux SSE**, et le DOD exige une étape de grille
qui mesure « déclenchement → **évènement reçu** ».

## Ce qui a été vérifié (et non supposé)

| Vérification | Résultat |
|---|---|
| Version k6 | `v1.4.2` (windows/amd64) |
| Module `k6/experimental/sse` | **absent** — `unknown dependency : k6/experimental/sse` |
| `go` disponible | **non** (`command not found`) |
| `xk6` disponible | **non** (`command not found`) |
| Endpoint SSE côté serveur | ✅ existe — `GET /api/v1/mail/events/stream?folder=…`, `text/event-stream`, identité résolue depuis la claim `mssEmail` (jamais `?email=`), abonnement clé `(mailbox, folder)` |
| Endpoint async côté serveur | ✅ existe — `POST .../emails/enrich/async` (`MailController:317`) |
| Métrique « connexions SSE actives » | **n'existe pas** — aucun compteur dans `SseMailEventBroker`, aucun `mssante_sse_*` |

SSE a été retiré des modules `experimental` de k6 en v1.x ; il n'existe plus que sous
forme d'**extension xk6**, qui demande un binaire k6 recompilé (donc Go + xk6).

## Pourquoi je ne livre pas « la partie faisable »

Sur les 6 critères du DOD, **5 sont réalisables** sans SSE lisible :

1. maintenir une connexion SSE par médecin — faisable en tenant la requête ouverte
   (`http.get` avec un délai égal à la durée du tir) : la connexion est **réellement**
   ouverte côté serveur, même si le client ne sait pas décoder ce qui y passe ;
2. faire passer l'enrichissement par la voie **async** — trivial ;
3. **⛔ mesurer déclenchement → évènement reçu — IMPOSSIBLE** : `http.get` bufferise,
   il ne rend la main qu'à la fermeture. Aucun évènement n'est observable en cours de
   route ;
4. compter les connexions SSE dans les coûts résidents — faisable, mais demande
   **d'abord** d'ajouter la métrique côté serveur (elle n'existe pas) ;
5. écrire la rupture de comparabilité dans `reports/INDEX.md` — trivial ;
6. tir 500 distant — exige le banc, différable comme sur les autres US.

**Et pourtant livrer 1-2-4-5 sans 3 serait un mauvais échange.** Passer le parcours en
async + SSE **casse la comparabilité** avec tous les tirs antérieurs de l'EPIC — le
DOD l'exige d'ailleurs par écrit (critère 5). On paierait donc le **coût entier** de la
rupture pour n'en récupérer qu'une partie du bénéfice : le coût résident serait mesuré,
mais la **latence perçue** — la raison même pour laquelle la US veut changer de voie —
resterait inconnue. Le tir suivant ne pourrait se comparer ni à l'ancien parcours, ni
au parcours cible.

C'est exactement le motif de la règle 11 (« pas de fausse v1 »), appliqué à
l'outillage de mesure.

## Ce qu'il faut décider

**Option A — recompiler k6 avec `xk6-sse`** (celle que je recommande)

Installer Go, puis `xk6 build --with github.com/phymbert/xk6-sse`, et faire pointer
`run.sh` sur ce binaire. C'est la seule voie qui livre le DOD **entier**.
Contrepartie : le banc dépend d'un binaire k6 **maison**, à reconstruire à chaque
montée de version — à documenter dans `docs/loadtest.md` et à installer sur toute
machine qui tire.

**Option B — livrer 1-2-4-5, retirer le critère 3 du DOD**

Le banc éprouverait alors le **coût résident** des 500 connexions (le point n°1 des
« trois choses non mesurées » de la US) sans mesurer la latence perçue. Il faut alors
assumer explicitement la rupture de comparabilité pour un bénéfice partiel, et rouvrir
une US pour le critère 3.

**Option C — mesurer la latence perçue par sondage, pas par évènement**

Déclencher en async puis interroger l'état d'enrichissement en boucle. **Je le
déconseille** : on mesurerait la fraîcheur d'un sondage, pas la poussée d'un
évènement — c'est-à-dire une voie que le produit n'emprunte pas. C'est précisément la
famille de substitution qui a coûté task-222 à cette EPIC (une conclusion tirée d'une
mesure qui ne mesurait pas ce que son nom annonçait), et que task-224 puis task-244
ont passé deux US à ré-outiller.

## Note pour l'implémentation, quelle que soit l'option

Deux points du DOD demandent du **code serveur**, pas seulement du harnais :

- la **métrique de connexions SSE actives** (`mssante_sse_connections_active`,
  sur le modèle de `mssante_imap_sessions_active` de task-211) — sans elle, la
  ligne des coûts résidents restera vide, et une ligne vide se lit « aucune
  connexion », c'est-à-dire l'inverse de la vérité (task-214) ;
- rien d'autre : la voie async et le flux SSE existent déjà et sont authentifiés
  comme la US l'exige.

Le contrôle de **confidentialité** exigé par la US (« chaque médecin ne reçoit que
**ses** évènements ») est testable dès qu'un client sait lire le flux — donc en
Option A seulement. En Option B il resterait non éprouvé, et c'est un point de
conformité, pas de performance : il primerait sur toute conclusion de charge.

---

## ⏸️ Décision humaine — 2026-08-09

**« Supprime 246, on traitera ce changement plus tard. »**

Task retirée du backlog actif et déplacée dans `tasks/onhold/todo-task-246.md`
(même mécanique que task-171/172), plutôt qu'effacée : l'énoncé du PO et l'analyse
ci-dessus sont précisément ce dont la réactivation aura besoin.

**Aucune des trois options A/B/C n'est tranchée** — le choix est *reporté*, pas fait.
Il se reposera sur des chiffres, après un tir 500 exerçant task-244 et task-245.

Si le fichier doit réellement disparaître, un `git rm` suffit — l'historique le
conserve de toute façon.
