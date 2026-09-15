# questions/task-313.md — une trace d'audit sans praticien nommé

> Constat de code review du 2026-09-15, pendant `/review task-313`.
> **Non bloquant** : la chaîne a continué, la US est verte et les PRs sont
> ouvertes. Ce point est une **question de conformité**, pas un défaut
> technique, et il appelle un arbitrage plutôt qu'un correctif improvisé.

## Le constat

task-313 pose `[MailboxNotRequired]` sur `POST /api/v1/sync/logout`. C'est le
bon attribut : la portée de cette route est *(praticien, session cliente)*, elle
ne touche aucune messagerie, et sans lui le praticien qui vient de détacher sa
dernière boîte ne peut plus se déconnecter proprement.

Conséquence non prévue par le DOD : **cette route est la première route
`[MailboxNotRequired]` qui émet une trace d'audit.** Les autres
(`ListMailboxesAsync`, `DetachMailboxAsync`, `SetDefaultMailboxAsync`) n'en
émettent aucune.

Or sur ce chemin, `userContext.Email` est **vide par conception** — et c'est
documenté comme tel dans le middleware :

> « Une requête sans boîte garde une adresse vide — c'est l'état d'un compte qui
> n'a encore rien rattaché, pas une anomalie, et c'est exactement ce que les
> routes `[MailboxNotRequired]` servent. » *(UserContextEnricherMiddleware)*

Et `AuditService` construit l'identité de la trace ainsi :

```csharp
UserId = _userContextInfo.Email ?? string.Empty,
```

**Donc** : une déconnexion sans boîte ouverte écrit une trace
`MailboxSessionClosed` avec `UserId = ""` et `FromAddress = ""`. Une trace que
personne ne peut attribuer.

## Ce que ça ne remet PAS en cause

- **Ce n'est pas une régression.** Avant task-313, cette requête était refusée
  en 403 et **aucune trace n'était écrite du tout**. Le changement ajoute une
  trace anonyme là où il n'y en avait aucune — il n'en dégrade aucune.
- **Ce n'est pas un trou de sécurité.** L'authentification du praticien reste
  exigée ; l'attribut n'exempte que l'exigence de messagerie.
- **Aucun risque de purge croisée.** Vérifié : `CleanupUserAsync` n'utilise
  `userEmail` que comme **clé de recherche** (`TryGetValue`,
  `HasActiveSessionsForEmail`, `GetStateAsync`). Une chaîne vide ne correspond à
  rien — l'appel est un no-op, jamais un effacement de masse. C'était le risque
  qui méritait d'être levé, et il est absent.

## ❓ Question au PO / responsable conformité

**Que doit-on faire d'un évènement de clôture quand il n'y a aucune messagerie
à fermer ?** Trois réponses possibles, et elles ne coûtent pas la même chose :

1. **Ne pas émettre la trace.** `MailboxSessionClosed` décrit une *frontière de
   session de boîte* (task-303). Sans boîte, il n'y a pas de session de boîte,
   donc pas de frontière. C'est le plus cohérent sémantiquement — mais le DOD de
   task-313 demande que l'évènement soit « toujours journalisé », donc ce choix
   doit être **explicitement** validé, pas décidé par un agent.

2. **Émettre la trace avec une identité de repli** — le `sub` PSC ou le RPPS,
   déjà présents dans le contexte de la requête. L'imputabilité PGSSI-S est
   préservée sans mentir sur l'adresse. **C'est ce que je recommande**, mais
   cela modifie la résolution d'identité d'`AuditService`, qui sert **toutes**
   les traces : le rayon d'action dépasse largement cette US.

3. **Statu quo** — assumer la trace anonyme, au motif qu'elle vaut mieux que
   l'absence de trace d'avant. Défendable, mais alors il faut le graver quelque
   part, sinon le prochain lecteur du journal prendra ces lignes vides pour un
   bug.

## Pourquoi je ne l'ai pas corrigé dans task-313

- **Règle 7c / règle 6** : l'option 2 touche `AuditService`, hors du module de
  la US, et affecte toutes les traces de la plateforme.
- **Règle de `/review`** : la forge ne corrige pas de code à l'étape de review.
- **Et un motif de fond** : choisir entre « pas de trace » et « trace sous une
  autre identité » est une décision de **conformité**, pas de programmation.
  L'improviser dans un correctif d'ergonomie serait exactement le genre de
  raccourci que la checklist santé existe pour empêcher.
