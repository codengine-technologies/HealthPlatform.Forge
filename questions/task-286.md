# questions/task-286.md — Aligner `client-angular` et `client-blazor` sur l'en-tête `Client-Session-Id`

> **Statut** : constat à faire avant de figer la US.
> **Ouvert le** : 2026-09-01
> **Mis à jour le** : 2026-09-01 — ajout de la **question 0**, qui prime sur
> toutes les autres, et du constat que les trois frontends partagent le même
> chemin d'authentification.
> **Origine** : question humaine posée en marge de `todo-task-285`.
> **Séquencement décidé** : après task-285. Ce n'est pas un prérequis.
> **Epic pressenti** : E009

---

## Le sujet

`client-mobile` envoie un identifiant de session cliente dans un en-tête depuis
task-282. `client-angular` et `client-blazor` ne l'envoient pas : le backend
retombe sur l'identifiant de session du fournisseur d'identité, puis sur
l'identifiant du jeton, puis sur une valeur littérale.

task-282 s'était explicitement arrêtée avant eux :

> `client-angular` et `client-blazor` : ils continuent de fonctionner par le
> repli sur `sid`. **Leur alignement est une US séparée.**

C'est cette US.

## Ce qui est établi

**Le défaut corrigé par task-282 était sévère.** Mesuré le 2026-08-30 sur **un
seul praticien en 34 minutes** : 27 sessions IMAP créées, reconnexion IMAP+SMTP
complète à chaque refresh, cache d'UIDs jeté, pools orphelins réapés au bout de
5 min. L'arithmétique décisive : 5 réplicas × 2 générations = **10 sessions IMAP
simultanées pour un praticien**, soit exactement le plafond de 10 connexions par
utilisateur imposé par l'opérateur.

**Mais ce défaut ne concernait pas les jetons porteurs d'un identifiant de
session.** Il portait sur des jetons qui n'en avaient **aucun** et retombaient
donc sur l'identifiant du jeton, unique par jeton (RFC 7519) — donc renouvelé à
chaque refresh.

**`client-angular` n'était pas dans ce cas le 2026-09-01** — un relevé
ponctuel, pas une propriété acquise. Deux jetons Angular successifs relevés dans
la console du navigateur, séparés de 300 s et d'un refresh :

| | identifiant du jeton | émis à | identifiant de session |
|---|---|---|---|
| Jeton A | `onrtac:08895e37…` | 1788290087 | `POknZQWE7knUZp8ghOae6MHX` |
| Jeton B | `onrtrt:b27f01a6…` | 1788290197 | `POknZQWE7knUZp8ghOae6MHX` |

L'identifiant du jeton change, celui de session **ne change pas**. Angular ne
subit donc pas le churn **au moment de cette observation** — voir la question 0,
qui met cette conclusion sous condition.

**Les trois frontends passent par le même chemin d'authentification.** Vérifié
le 2026-09-01 : `client-blazor` (`AuthService`, `TokenService`,
`PscTokenRefreshService`), `client-angular`
(`lib/auth/interceptors/utils/auth-interceptor.utils.ts`) et `client-mobile`
(`core/auth/auth.service.ts`) appellent tous les **mêmes** endpoints du proxy —
`/auth/token`, `/auth/refresh`, `/session/token`.

Ce n'est donc pas « mobile est un cas particulier ». Ce qui fait apparaître ou
disparaître l'identifiant de session agit sur les trois frontends de la même
façon. Conséquence directe : la US doit couvrir `client-angular` **et**
`client-blazor` ensemble, et l'en-tête client est le seul moyen de sortir les
trois de cette dépendance commune.

## Ce qui n'est pas établi — le constat à faire

**Question 0 — pourquoi le même client porte-t-il un identifiant de session
aujourd'hui et pas il y a deux jours ? (à lever EN PREMIER)**

Deux observations contradictoires, à deux jours d'écart, sur la **même**
configuration :

| Date | Source | Client | Identifiant de session | Identifiant de jeton |
|---|---|---|---|---|
| 2026-08-30 | task-282, jeton décodé | `weda` | **aucun** | `trrtag:ebead400…` |
| 2026-09-01 | jeton Angular, console navigateur | `weda` | `POknZQWE…`, **stable** | `onrtac:…` / `onrtrt:…` |

task-282 citait task-275 à l'appui : « aucune session pour le client `weda` —
session transiente ». Le jeton du 2026-09-01 porte, lui, `identity_provider:
"oidc"` — signe d'un vrai flux de login Keycloak avec session, et non du
token exchange RFC 7523 sans session décrit par task-282.

Deux lectures possibles, non départagées :
- **la configuration a changé** entre les deux dates (côté proxy ou côté realm),
  et personne ne l'a décidé ni remarqué ;
- **les deux contextes d'observation diffèrent** d'une manière non identifiée
  (chemin de login emprunté, client applicatif réellement utilisé, etc.).

**Pourquoi cette question prime.** Tant qu'elle n'est pas levée, on ne sait pas
dans quel état est le système, donc :
- la santé actuelle d'Angular peut être **accidentelle et réversible**, pas
  acquise ;
- mesurer Blazor (question 1) donnerait un résultat **non reproductible** — on
  ne saurait pas si on observe un état stable ou un état transitoire.

**Et cette question est déjà, en soi, un argument pour la US.** La formulation
initiale — « la stabilité de l'identifiant de session n'est garantie par rien » —
est trop douce. Elle est **empiriquement instable** : elle a déjà changé une
fois, sans décision ni signal. La US passe donc d'hygiène préventive à correctif
sur une bascule déjà constatée.

Piste d'investigation : comparer les journaux du proxy et la configuration du
realm entre le 2026-08-30 et le 2026-09-01, et déterminer quel flux
(`/auth/token` après callback vs token exchange) a servi dans chaque cas.

**Question 1 — `client-blazor` est-il, lui, en churn silencieux ?**

> **Dépend de la question 0.** Mesurer Blazor sans savoir dans quel état est le
> système donnerait un résultat non reproductible. Lever la question 0 d'abord.

Je n'ai la preuve de stabilité que pour Angular, et à un seul instant. Blazor
peut très bien recevoir des jetons sans identifiant de session, donc retomber
sur l'identifiant de jeton, donc reproduire exactement le défaut de task-282
sans que personne ne l'ait mesuré.

Protocole proposé, ~15 minutes — **à jouer sur Blazor ET sur Angular**, pour
disposer des deux mesures dans le même état de configuration :

1. Démarrer le backend via l'AppHost (profil `https`, 5 réplicas).
2. Ouvrir `client-blazor`, se connecter, charger la boîte de réception.
3. Relever dans la console du navigateur deux jetons successifs séparés d'un
   refresh (~5 min d'écart), et comparer leurs identifiants de session. Noter
   aussi la présence de `identity_provider` et le préfixe de l'identifiant de
   jeton (`trrtag:` vs `onrtac:`/`onrtrt:`) — c'est ce qui distingue les deux
   flux mis en évidence par la question 0.
4. En parallèle, compter dans Seq les créations de session de messagerie pour ce
   praticien sur 10 minutes d'usage normal.

Lecture du résultat :
- **Identifiant de session stable + nombre de sessions ≈ nombre de réplicas
  touchés** ⇒ Blazor est sain comme Angular. La US devient de l'**hygiène**
  (supprimer une dépendance à un comportement non contractuel), priorité basse.
- **Identifiant absent ou changeant, ou créations de session en escalier** ⇒
  Blazor est en churn. La US devient un **correctif de production** qui pousse
  contre le plafond de connexions de l'opérateur, priorité haute.

**Question 2 — quelle priorité si les deux frontends sont sains ?**

> **Probablement sans objet depuis la question 0.** Si l'identifiant de session
> a déjà basculé une fois entre le 2026-08-30 et le 2026-09-01, « sain
> aujourd'hui » ne veut plus dire « sain », et la US est un correctif quel que
> soit le résultat de la question 1. Cette question ne se pose que si la
> question 0 établit que rien n'a bougé et que les deux observations
> s'expliquent par des contextes différents et maîtrisés.

Dans ce cas, les trois justifications restantes sont :

1. **Supprimer une dépendance non contractuelle.** La stabilité de l'identifiant
   de session dépend du comportement du proxy d'identité, pas d'un contrat.
   task-282 l'a formulé : *« Aucun réglage côté Keycloak ni côté proxy ne peut
   stabiliser cette valeur — seul un identifiant fourni par le client peut
   l'être. »* Le jour où le chemin Angular passe par un proxy qui re-frappe le
   jeton au lieu de le rafraîchir, il bascule dans le scénario à 27 sessions
   sans que personne ne l'ait décidé.
2. **Rendre uniforme le périmètre de la règle 2 de task-285.** Aujourd'hui, sur
   Angular et Blazor, « fermer la session cliente courante » ferme en réalité la
   session d'authentification entière : deux onglets du même praticien se
   déconnectent ensemble. Avec l'en-tête, la règle veut dire la même chose
   partout.
3. **Aucune surveillance.** Rien n'alerte aujourd'hui si le nombre de sessions
   par praticien se met à grimper. Le churn de task-282 a été trouvé à la main,
   pas par un signal.

À l'humain de dire si ça justifie une US à part entière ou si ça part au
backlog long.

**Question 3 — faut-il en profiter pour poser une garde ?**

Si l'alignement se fait, faut-il **cesser** de retomber sur les claims du jeton
une fois les trois frontends équipés (repli devenu du code mort et un piège
silencieux), ou garder le repli indéfiniment pour tout client tiers ?

## Ce que la US produira, une fois ces réponses obtenues

- **Repos** : `client-angular`, `client-blazor`, et `api-mail` seulement si la
  question 3 conduit à retirer le repli.
- Un identifiant de session engendré au login, persisté avec la session locale,
  stable tant que le praticien ne se déconnecte pas — le modèle déjà retenu par
  `client-mobile` en task-282.
- Une mesure **avant / après** du nombre de sessions de messagerie créées par
  praticien sur une fenêtre donnée : c'est elle qui prouvera le gain, ou son
  absence.
