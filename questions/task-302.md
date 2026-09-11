# questions/task-302.md — Livrée à moitié : le quota est éprouvé, le cloisonnement ne l'est pas

**Task** : task-302 (EPIC E016) — reste en **`wip-*`**
**Branche** : `feat/task-302-capacites-serveur-test` (poussée, commit `2589a8c1`), **pas de PR** — le DOD n'est pas atteint
**Date** : 2026-09-11

---

## Ce qui est livré et vert

1. **`DovecotTestConfig`** — la configuration de test est **dérivée** de celle du
   banc au lieu d'être copiée : elle lit `src/AppHost/dovecot/dovecot.conf` et
   lui ajoute la capacité `QUOTA` et les dossiers `Junk`/`Archive`. La détection
   de régression de configuration **survit** (le contenu du banc est toujours
   celui qui s'exécute) et le banc n'est **pas touché** — ses réglages sont
   justifiés par la mesure et E015 en dépend. Les ancres d'insertion **lèvent**
   si elles disparaissent, plutôt que de produire une configuration
   silencieusement incomplète.
2. **`MailboxQuotaRealServerTests`** (3 tests, verts) — le premier
   `GETQUOTAROOT` jamais émis par la suite. Assertions sur la **capacité
   annoncée par le serveur** (et pas seulement sur le résultat du service), sur
   le total exact issu de la règle configurée, et sur la cohérence du
   pourcentage avec ses deux entrées.
3. **4 indices d'utilisateur virtuel réservés** (6 à 9), garde portée à 19.

Validation : **493 tests, 0 échec**.

## La découverte qui dépasse la task

`UserContextInfo.IsOnlineMode` vaut `!string.IsNullOrEmpty(PscToken)`, et
**aucune identité du harnais ne porte de jeton PSC**. Conséquence :

> **Toute la suite à serveur réel s'exécute en mode hors-ligne.**

Les services IMAP de lecture ne s'en aperçoivent pas — ils n'interrogent pas le
mode. Mais **tout chemin gardé par `CanAccessImap` / `CanSendEmail` /
`CanModifyFlags` était inexercé**. `MailboxQuotaService` commence précisément
par `if (!_connectionModeService.CanAccessImap) return Available = false;` : son
chemin nominal était **doublement** inatteignable — capacité absente du serveur
**et** scope hors-ligne.

J'ai posé un jeton factice **localement dans la nouvelle suite** plutôt que de
changer l'identité partagée du harnais : basculer les 97 tests existants en mode
en ligne changerait le comportement de chemins que personne n'a examinés sous
cet angle, et ce n'est pas une décision de `/develop`. **C'est le premier point
d'arbitrage.**

## Ce qui manque au DOD — et pourquoi je n'ai pas continué

| Item du DOD | État | Raison |
|---|---|---|
| Capacité `QUOTA` annoncée + `GetQuotaAsync` nominal + dépassement | ✅ les 2 premiers ; ❌ **le dépassement** | Remplir une boîte au-delà de 50 Mo demande un corpus dédié ; faisable, non fait |
| `Junk` / `Archive` résolus **par `special_use`** | ⚠️ déclarés dans la conf, **pas de test** | Aucune API applicative n'expose la résolution de dossier spécial : l'assertion « par attribut et non par repli sur le nom » exige soit une API, soit une sonde IMAP qui doublerait le code de production. Choix à faire. |
| Cloisonnement inter-praticiens (lecture, marquage, déplacement) | ❌ **non fait** | Voir ci-dessous — c'est le vrai sujet |
| Comptes distincts par praticien (`passdb` par fichier) | ❌ **non fait** | Voir ci-dessous |
| Échec d'authentification différencié | ⚠️ partiellement pré-existant (`DovecotBenchSmokeTests.WildcardAuth_...`) | Le reste dépend du `passdb` |

### Le point dur : `passdb static` ne peut pas être remplacé par ajout

La configuration du banc déclare `passdb { driver = static; args = password=loadtest }`.
Ma génération **ajoute** à la configuration du banc — elle ne la réécrit pas,
et c'est ce qui préserve la détection de régression. Or ajouter un second
`passdb` ne remplace pas le premier : Dovecot les essaie dans l'ordre, et le
`static` accepte **tout utilisateur**. Le cloisonnement resterait donc
inéprouvable au niveau du serveur.

Deux sorties possibles, et c'est **le second point d'arbitrage** :

- **A — remplacer le bloc `passdb` par substitution textuelle** dans la
  configuration dérivée, avec un `passwd-file` généré depuis la table
  `VirtualUsers`. Techniquement propre, mais cela crée une **seconde ancre**
  dans la configuration du banc, donc un second point de rupture.
- **B — déplacer l'assertion de cloisonnement au niveau d'api-mail** plutôt
  qu'au niveau de Dovecot : affirmer que, dans le scope du praticien A, les
  services ne rendent **jamais** un message portant le marqueur de corpus du
  praticien B (`LoadTestPlanGenerator.OwnerMarker`). **C'est la propriété
  produit qui compte** — que notre code ne franchisse pas la frontière — et
  elle est éprouvable avec le `passdb` wildcard actuel, sans toucher à la
  configuration du banc.

**Je recommande B**, et je pense que le DOD devrait être corrigé en ce sens :
tester que Dovecot refuse un mauvais mot de passe teste Dovecot ; tester
qu'api-mail ne sert jamais la boîte d'un autre teste **notre** produit.

## Ce que je demande

1. Mode en ligne : bascule-t-on l'identité **partagée** du harnais (et on
   examine ce que cela change sur les 97 tests), ou reste-t-on sur un jeton
   posé localement par les suites qui en ont besoin ?
2. Cloisonnement : option **A** (passwd-file, niveau serveur) ou **B**
   (assertion au niveau api-mail, recommandée) ?
3. Une fois tranché, task-302 se termine vite : la conf dérivée et le socle sont
   en place, il ne reste que les suites.

La branche est poussée et verte ; **aucune PR n'a été ouverte** puisque le DOD
n'est pas atteint. La task reste `wip-*`.
