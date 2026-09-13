# questions/task-302.md — Accès admin / sécurité au journal d'audit mutualisé : qui est « admin », et comment s'authentifie-t-il ?

**Statut** : bloquant — la US `task-302` n'est **pas** rédigée tant que ce point n'est pas
arbitré. Checklist conformité `agents/po.md` point 2 (authentification PS) et point 3
(habilitations).
**Epic**: E016
**Ouverte le** : 2026-09-13, sur demande : « les admins et la sécurité doivent pouvoir y accéder »

---

## Ce que j'ai vérifié dans le code avant de poser la question

**Il n'existe aujourd'hui aucun modèle de rôles dans `api-mail`.**

- `src/Api/Program.cs:133` — la seule politique d'autorisation est une *fallback policy*
  `RequireAuthenticatedUser()`. Elle exige un jeton valide, **rien d'autre**.
- `src/Api/Controllers/V1/BiologyAcksController.cs:15` — commentaire explicite :
  « The Doctor role gate was disabled on 2026-05-11 (*on accepte tout le monde pour le
  moment*) ». Le gate de rôle a donc existé, puis a été retiré.
- `src/Api/Controllers/V1/AuditController.cs` — aucune politique, aucun rôle. L'écran d'audit
  est protégé **uniquement** par deux choses : la frontière de base PostgreSQL, et le
  `WHERE t.UserId == UserContextInfo.Email` du repository.

**Conséquence directe.** Aujourd'hui, *tout utilisateur authentifié* passe *tous* les
endpoints. Ce qui empêche un praticien de lire les traces d'un autre n'est pas une
autorisation : c'est le fait qu'il n'atteint physiquement pas l'autre base.

Or task-300 supprime précisément cette frontière physique pour le journal, et la demande
d'accès admin consiste à **ouvrir volontairement** une lecture transverse sur une table qui
porte de la donnée de santé (`PatientIns`, `PatientName`, `Subject`, `DocumentId`,
`FromAddress`) pour **tout le parc**.

Ouvrir cet accès sans modèle d'autorisation reviendrait à créer un endpoint dont la seule
protection serait « être authentifié » — c'est-à-dire accessible à n'importe quel praticien du
parc. **Je refuse de rédiger la US dans cet état.**

---

## Questions à arbitrer

### 1. Identité des administrateurs (bloquante)

Les praticiens s'authentifient par PSC / e-CPS via Keycloak. Un administrateur d'exploitation
ou un analyste sécurité **n'est pas un professionnel de santé** et n'a pas de carte CPS.

- D'où vient son identité ? (annuaire interne Keycloak dédié, IdP d'entreprise, autre)
- Quel niveau d'authentification exige-t-on ? La PGSSI-S impose un niveau d'autant plus élevé
  que l'accès porte sur des données de santé de **plusieurs** patients de **plusieurs**
  praticiens. **Recommandation : MFA obligatoire, sans exception, et aucun accès par compte
  partagé** (un compte nominatif par personne, sinon l'imputabilité du journal est perdue).

### 2. Deux niveaux d'accès, ou un seul ? (bloquante)

Je recommande **deux**, parce que 90 % des besoins réels ne nécessitent aucune donnée de santé :

| Niveau | Ce qu'il voit | Pour qui |
|---|---|---|
| **Exploitation** | volumétrie, taux d'erreur, types d'action, horodatages, identifiants de tenant — **aucune** donnée patient, aucun sujet de message | supervision, diagnostic d'incident, capacité |
| **Investigation** | la trace complète, **DSCP comprises** | sécurité, réponse à incident, réquisition, contrôle CNIL/ANS |

Le second doit être **motivé, borné dans le temps, et lui-même journalisé**. Est-ce le
découpage voulu, ou un seul niveau suffit-il ?

### 3. L'accès admin est-il lui-même journalisé ? (recommandation : oui, non négociable)

La PGSSI-S traite l'**accès aux journaux** comme un évènement à journaliser. Concrètement :
toute consultation de traces par un administrateur produit elle-même une trace (qui a consulté,
quand, quel périmètre, quelle justification), **dans un journal que l'administrateur ne peut
pas modifier**. Sans cela, le journal d'audit cesse d'être opposable le jour où on en a besoin.

Confirmez-vous ce méta-journal, et sa rétention (recommandation : alignée sur la rétention des
traces d'accès aux données de santé, 3 653 jours) ?

### 4. Portée d'un accès d'investigation

Un analyste peut-il interroger **tout le parc** d'un coup, ou l'accès doit-il être **cadré**
(un tenant, une fenêtre de temps, un motif saisi) ? **Recommandation : cadré.** Un endpoint qui
rend « toutes les traces de tous les praticiens » est une fuite en attente d'un identifiant
compromis.

### 5. Où vit cet accès ?

Écran dans `client-blazor` ? Endpoint API consommé par un outil interne ? Requête SQL
documentée dans un runbook, sans endpoint du tout (le moins de surface exposée, mais pas
d'imputabilité applicative) ? Cette réponse détermine les `**Repos**:` de la US.

---

## Ce que je propose, si vous voulez trancher vite

1. Restaurer un modèle de rôles dans `api-mail` (la fallback policy reste, les rôles
   s'ajoutent) — **c'est une US à part entière et un préalable**, indépendamment du journal.
2. `task-302` = accès **Exploitation** seul (aucune DSCP), endpoint cadré, méta-journal.
   Faible risque, couvre la supervision.
3. `task-303` = accès **Investigation** (DSCP), cadré par tenant + fenêtre + motif, MFA,
   méta-journal, validation DPO spécifique.

Répondez au moins aux points 1 et 2 et je rédige les `todo-*.md` dans la foulée.

---

## Ce qui n'est **pas** bloqué par cette question

`task-299` (annuaire), `task-300` (journal mutualisé) et `task-301` (reprise) sont rédigées et
prêtes : **aucune n'ouvre d'accès transverse**. Le praticien continue de ne voir que ses
propres traces, et task-300 en **renforce** la garantie (RLS en base, là où il n'y avait qu'un
filtre applicatif). L'accès admin s'ajoutera par-dessus, une fois ce point tranché.
