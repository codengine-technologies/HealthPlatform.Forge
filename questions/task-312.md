# questions/task-312.md — Arbitrage requis : où vont les traces d'audit **sans tenant** ?

> Écrit par `/develop 312` le 2026-09-14. **Fail-fast** : la chaîne s'arrête ici. Rien
> n'est committé ni poussé — le travail déjà fait reste dans l'arbre de travail d'
> `api-mail`, sur `chore/task-312-retrait-audit-herite`.

## Le blocage

L'US demande de retirer la table d'audit héritée et son dépôt. En implémentant, j'ai
découvert que **le dépôt hérité n'est pas seulement un vestige : c'est le chemin d'écriture
nominal d'une partie des traces.**

`AuditBackgroundService` partage le lot en deux, et le commentaire du code le revendique :

```csharp
var mutualised = batch.Where(t => t.TenantId.HasValue).ToList();   // → journal mutualisé
batch = batch.Where(t => !t.TenantId.HasValue).ToList();           // → base praticien
```

> *« Les autres — registre désactivé, tenant non résolu, trace émise avant la bascule —
> gardent l'ancien chemin. Ce n'est PAS une dette : c'est ce qui permet à cette US de
> s'installer sans que le journal dépende de la présence du registre. »*

**Retirer la base praticien enlève donc la destination des traces sans `TenantId`.**

## Quelles traces sont concernées

`AuditService` estampille `TenantId = _userContextInfo.TenantId` à l'émission. Ce champ est
nul **chaque fois qu'aucune boîte n'est résolue** — et depuis task-308, c'est un état
nominal, plus une exception :

| Trace | Où | TenantId à l'émission |
|---|---|---|
| `MailboxAttached` | `MailboxManagementService.cs:110` | **nul** — le middleware a tourné avant le rattachement |
| `MailboxDetached` | idem | nul si la boîte détachée était la seule |
| `MailboxSessionOpened` | `UserContextEnricherMiddleware.cs:257` | dépend du moment de la résolution |
| Échecs d'authentification, routes `[MailboxNotRequired]` | divers | nul |

`MailboxAttached` et `MailboxDetached` sont classées **accès aux données de santé** par
`AuditRetentionPolicy` (rétention 3 653 jours) : ce sont des évènements de sécurité, pas
du bruit technique.

## Les trois issues, et ce qu'elles coûtent

**A — Estampiller le tenant à la source.** Les sites qui *connaissent* leur tenant le
posent explicitement (`AttachAsync` a le `tenant.Id` en main juste après l'écriture). Bonne
solution là où elle s'applique, mais **elle ne couvre pas tout** : un échec
d'authentification avant toute résolution n'a aucun tenant à poser. Il restera des traces
sans tenant.

**B — Tenant sentinelle (`Guid.Empty`) dans le journal mutualisé.** Rien n'est perdu, tout
est conservé et purgé par la rétention. **Mais ces traces deviennent invisibles dans
l'écran d'audit de tout praticien** : la RLS filtre sur `tenant_id`, et `Guid.Empty`
n'appartient à personne. Aujourd'hui, `MailboxAttached` est visible par le praticien
concerné (le dépôt hérité filtre sur `UserId == email`). **On perdrait cette visibilité sur
un évènement de sécurité qui le concerne directement.**

**C — Garder le dépôt hérité pour ces seules traces.** Contredit l'US : la table reste,
avec sa purge, son dépôt et sa double lecture.

## Ce que je recommande

**A + B combinés** : estampiller partout où le tenant est connu (ce qui couvre
`MailboxAttached`, `MailboxDetached` et l'essentiel des évènements de session), et router
le résiduel vers le tenant sentinelle avec un commentaire disant pourquoi il n'est visible
de personne.

Mais **B a une conséquence de conformité que je ne peux pas trancher seul** : rendre
invisible au praticien un évènement de sécurité qui le concerne. C'est une décision de PO
et de conformité, pas d'implémentation.

## Question

**Acceptes-tu que les traces résiduelles sans tenant deviennent invisibles dans l'écran
d'audit du praticien (option B), ou faut-il leur garantir une visibilité — auquel cas il
faut décider comment, la RLS étant l'isolation ?**

## État du travail

Fait dans l'arbre de travail, **non committé** :

- `AuditRetentionHostedService` **créé** — la purge du journal mutualisé est branchée
  (c'était le premier item du DOD, et le vrai blocage légal du retrait).
- Machinerie de reprise **supprimée** (`AuditBackfill*`, 6 fichiers).
- `PostgresAuditReader` **réduit à une source**.
- `AuditController` **sans repli**, rend une page vide sans tenant.

Reste à faire, suspendu à l'arbitrage : le drain, le dépôt hérité, la table, les deux
marques, les tests.

**L'arbre ne compile pas en l'état** — c'est volontaire : committer un retrait à moitié
serait pire que de le laisser visible.
