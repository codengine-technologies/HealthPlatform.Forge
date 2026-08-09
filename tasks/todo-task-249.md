# todo-task-249.md — La sonde de bonne santé fausse la mesure sur laquelle on dimensionne la base

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune
**Priorité**: **2** — gain **nul** sur la latence du médecin, **tout** sur la
lisibilité de la mesure. Elle a masqué la vraie tendance pendant trois campagnes,
et deux verdicts d'A/B de pool ont été rendus sur la grandeur qu'elle contamine.

## Objective

Que la sonde de readiness cesse de traverser le multiplexeur de connexions, pour
que `cl_waiting` ne mesure plus que le **chemin du médecin**.

## Ce qui est établi

**Par lecture de code** : `AddNpgSql(postgresConnectionString)`
([DependencyInjectionExtensions.cs:211](../Api/Mail/src/Api/DependencyInjectionExtensions.cs#L211))
utilise la chaîne **serveur**, qui en profil loadtest pointe sur PgBouncer **sans
`Database=`** — le nom de base retombe alors sur l'identité, soit `postgres`.

**Par contre-épreuve au banc** (2026-08-08) : le pool `postgres` avait disparu par
expiration ; **un seul `GET /health` l'a recréé** (`cl_active=1`). Le chemin de
contrôle (provisionnement) est bien en direct, comme l'ADR le prescrit — c'est la
**sonde de santé** qui traverse le pooler.

**Effet mesuré**, avec la ventilation livrée par task-242 :

| Tir | Attente sur bases **praticien** | Attente sur le pool **`postgres`** |
|---|---|---|
| Local 200, 2026-08-08 | 3 ms à 50, 9 ms à 100, 1,10 s à 200 | **18,3 s** à 100, **23,4 s** à 200 |
| Distant 500, 2026-08-09 | 3,1 / 62,9 / **53,3 ms** | 1 relevé à **400 ms** |

Le total publié pendant trois campagnes **sommait ces deux populations sans
rapport**. Un pool de maintenance à `default_pool_size=2`, partagé par les cinq
réplicas, produisait des attentes de plusieurs dizaines de secondes qui n'ont
**rien à voir** avec le chemin de données du médecin.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que la profondeur de 18 à 62 s est une attente réelle.** Elle
  est **compatible** avec une entrée de file abandonnée — Npgsql renonce à 5 s de
  délai, PgBouncer continue de compter l'attente du plus vieux client tant que la
  socket n'est pas fermée, et le profil en dents de scie observé va dans ce sens —
  mais elle **n'est pas prouvée** : l'état des sockets clientes n'a pas été relevé.
  Ne pas la lire comme « un médecin a attendu 62 s ».
- **Ne pas présumer qu'il faut élargir le pool de maintenance.** Le remède est de
  **router** la sonde, pas de lui faire de la place.

## Definition of Done

- [ ] La sonde de readiness emprunte la chaîne **directe** (celle du chemin de
      contrôle, déjà disponible) ou cible sa propre base — plus jamais le pooler
- [ ] Contre-épreuve au banc : après un `GET /health`, **aucun** pool `postgres`
      n'apparaît dans `SHOW POOLS`
- [ ] La sonde continue de faire son travail : elle échoue toujours quand Postgres
      est réellement indisponible (test explicite, pas seulement le cas passant)
- [ ] Hors profil loadtest, le comportement est **strictement inchangé**
- [ ] Sur un tir, la ligne « pool de maintenance » de la table des coûts résidents
      est à **zéro** — c'est le critère observable

## Manual Test Plan

- Monter le banc, appeler `GET /health` puis `SHOW POOLS` sur PgBouncer :
  aucun pool `postgres` ne doit être créé
- Arrêter Postgres et rappeler `/health` : la sonde doit **échouer** (sinon on a
  supprimé la mesure au lieu de la router)
- Lancer un tir court et vérifier que `maxwait` du pool de maintenance vaut 0

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — exploitation
- **Exigences DSR honorées** : aucune
- **INS / Consentement / Interop CI-SIS / MSSanté** : non applicable
- **Authentification PS** : inchangée — la sonde reste non authentifiée comme
  aujourd'hui, et ne doit **rien** exposer de plus qu'un état
- **Habilitations** : ⚠️ le cloisonnement « une base par praticien » ne doit pas
  être affaibli : la sonde ne doit atteindre **aucune** base praticien
- **Sécurité** : aucun secret de chaîne de connexion dans les journaux
- **Tracé PGSSI-S** : non applicable
- **Hébergement HDS** : le routage retenu doit être transposable à la cible
- **AIPD / impact RGPD** : inchangé
