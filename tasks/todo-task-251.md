# todo-task-251.md — Cinq exceptions par seconde et par réplica, et personne ne sait de quelle famille

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune
**Priorité**: **3** — aucun symptôme utilisateur connu, mais c'est la **signature
exacte** d'un défaut déjà rencontré, et le banc ne peut pas l'écarter sans l'ouvrir.

## Objective

Nommer la famille d'exceptions qui représente **4,4 à 5,0 exceptions par seconde
et par réplica** sur un tir nominal, et décider ensuite — pas avant — s'il faut la
corriger.

## Ce qui est établi

Tir local 200 du 2026-08-08, table « Par réplica api-mail », **cinq réplicas** :

| Réplica | Exceptions /s |
|---|---|
| `…-122332` | 4,53 |
| `…-87892` | 4,58 |
| `…-89828` | 4,87 |
| `…-97668` | 4,96 |
| `…-99488` | 4,36 |

Le repère documenté est « **quelques unités**, pas des centaines » — on y est, mais
**l'homogénéité entre réplicas et la croissance avec la charge** sont la signature
d'un **coût par requête**, pas d'incidents.

**C'est exactement le profil de deux défauts déjà trouvés dans cette EPIC** :
`SecurityTokenMalformedException` (task-206, ~1,2 exception **par requête**, 12 668
occurrences en 121 s), et `ClientResultException` classée à tort chez Flagsmith
alors qu'elle venait d'OpenAI et signalait des documents cliniques **perdus pour la
recherche**. Dans les deux cas, la famille n'avait pas été ouverte.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est bénin parce que le total est faible.** La leçon de
  `ClientResultException` est précisément celle-là : une famille non ouverte peut
  masquer une perte fonctionnelle silencieuse.
- **Ne pas présumer que c'est encore `SecurityTokenMalformedException`.** Elle est
  censée valoir **0** depuis task-206 — si elle est revenue, c'est une régression à
  traiter comme telle, et c'est un résultat en soi.

## Definition of Done

- [ ] La ou les familles dominantes sont **nommées**, avec leur part respective,
      établies par `sum by (error_type) (increase(dotnet_exceptions_total[2m]))`
      sur la fenêtre d'un tir
- [ ] Pour chaque famille : le **chemin de code** qui la lève, et si elle est levée
      **une fois par requête** ou par incident
- [ ] Verdict écrit par famille : bénigne (avec la raison), ou défaut → **US
      dédiée** proposée au PO
- [ ] `SecurityTokenMalformedException` est **vérifiée à 0** — sinon régression
- [ ] Le repère « quelques unités par seconde » de `docs/loadtest.md` est **remplacé
      par un chiffre attendu et sa famille**, pour que le prochain tir puisse
      détecter une dérive au lieu de hausser les épaules

## Manual Test Plan

- Monter le banc, lancer un tir court (`journey`, 50 médecins, 5 min)
- Relever `sum by (error_type) (increase(dotnet_exceptions_total[2m]))` **à un
  instant situé dans la fenêtre du tir** (une `rate` évaluée après coup rend une
  série vide — piège documenté)
- Croiser avec Seq : pour la famille dominante, dérouler une trace complète et
  identifier le site d'appel

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — hygiène d'exploitation
- **Exigences DSR honorées** : aucune
- **INS** : non applicable — ⚠️ aucun message d'exception recopié dans le rapport ne
  doit contenir de donnée patient ; ne citer que le **type** et le site d'appel
- **Authentification PS** : ⚠️ si la famille dominante touche la validation du
  jeton PSC, le finding devient un sujet de **sécurité** et change de priorité
- **Habilitations / Consentement / Interop CI-SIS / MSSanté** : non applicable
- **Tracé PGSSI-S** : non applicable
- **Hébergement HDS** : sans objet
- **AIPD / impact RGPD** : inchangé
