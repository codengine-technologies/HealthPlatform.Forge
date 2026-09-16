# todo-task-314.md — Une messagerie détachée n'offre plus que « Rattacher », et dit quand elle l'a été

**Repos**: dtos-mss, api-mail, client-blazor, client-angular, client-mobile
**Dependencies**: **task-310** (en attente de merge — elle touche les mêmes
`confirmRemove` sur les trois fronts ; à merger avant, sinon conflit d'édition
sur les mêmes blocs)
**Epic**: E016

## Objectif

Sur l'écran de gestion des messageries, une ligne **détachée** propose
aujourd'hui « Définir par défaut » et « Supprimer ». Les deux sont sans objet.
Elle ne doit plus offrir que **« Rattacher »**, et afficher la date à laquelle
elle a été **détachée** plutôt que celle de son rattachement.

## Le constat, du 2026-09-16

Capture d'écran à l'appui, sur `client-angular`, après avoir coché « Afficher
les messageries détachées ». La ligne affiche :

```
virginie.medecinrpps0062267@…   medecin.formation.mssante.fr   Détachée
Rattachée le 2026-09-16T07:52:32.309421+00:00
[ ☆ Définir par défaut ]  [ 🗑 Supprimer ]
```

**Quatre choses ne vont pas**, et elles se voient toutes sur cette seule ligne.

### 1. « Définir par défaut » n'a pas de sens

Une boîte détachée ne peut pas s'ouvrir, donc pas être le défaut. Si l'action
aboutissait, elle poserait un défaut que la garde d'entrée ne pourrait jamais
honorer — `MailboxEntryDecision` ne retient que les boîtes **sélectionnables**.

### 2. « Supprimer » n'a pas de sens, et induit en erreur

Elle est déjà détachée. Le bouton laisse croire à une seconde suppression, plus
définitive, **qui n'existe pas et ne doit pas exister** (voir l'encadré
ci-dessous). Le texte de confirmation dit d'ailleurs « La messagerie ne sera
plus accessible depuis ce compte » — c'est déjà le cas.

### 3. « Rattacher » manque, là où on l'attend le plus

La capacité existe et elle est soignée : `AttachMailboxAsync` **réactive la
ligne détachée** au lieu d'en créer une seconde, explicitement pour préserver le
`TenantId` que le journal d'audit référence. Mais le seul chemin est de
**retaper l'adresse** dans le formulaire du dessous — sur une ligne qui
l'affiche déjà.

### 4. La ligne d'information ment

Elle dit « Rattachée le … » sur une ligne marquée « Détachée ». Pour une boîte
détachée, la date qui compte est celle du **détachement** : c'est elle qui
gouverne la conservation, et c'est ce que la confirmation a promis au praticien
(« vos données restent soumises aux règles de conservation »). `detached_at`
existe en base et au domaine (`RegistryTenant.DetachedAt`) — il **manque au
contrat**.

Accessoirement, la date est rendue brute (`2026-09-16T07:52:32.309421+00:00`).

---

> ### ⚠️ Pourquoi « Supprimer » disparaît au lieu d'être réparé
>
> Question posée par l'humain le 2026-09-16 : « supprimer doit la retirer
> définitivement de la liste pour permettre à un autre compte de s'y rattacher ».
> Vérification faite, **la suppression ne serait ni nécessaire ni sans danger**.
>
> **Ce n'est pas l'adresse qui bloque un autre compte**, c'est le RPPS —
> `rppsHeldElsewhere` balaie toutes les lignes, détachées comprises. C'est un
> défaut distinct, traité par sa propre US.
>
> **Et supprimer la ligne orphelinerait le journal d'audit.** Elle porte le
> `TenantId` que `audit_traces.tenant_id` référence — 152 traces sur 5 tenants
> au moment du constat — et il n'existe **aucune clé étrangère** : la
> suppression n'échouerait pas, elle romprait le lien en silence. Ces traces
> sont soumises à la journalisation PGSSI-S et à 6 ans de conservation ; elles
> doivent rester attribuables.
>
> **Décision humaine du 2026-09-16** : pas de suppression. Le lien prime.

---

## Ce que la US NE fait pas

- **Le prédicat `rppsHeldElsewhere`** — une ligne détachée continue de retenir
  le RPPS et empêche un autre compte de rattacher la messagerie. C'est un
  **défaut réel**, mais backend et distinct : il mérite sa propre US, et le
  mêler ici brouillerait une correction d'écran avec une règle d'annuaire.
- **Aucune clé étrangère n'est ajoutée** sur `audit_traces`. Analysée et
  écartée : le rôle d'écriture (`mss_audit_writer`) n'a que `INSERT` et aucun
  droit sur le registre — une FK l'obligerait à lire la table référencée ; la
  vérification par ligne pèserait sur le puits groupé (correctif de capacité de
  task-300) ; et `CASCADE` effacerait des traces quand `RESTRICT` interdirait
  toute purge légitime. Une trace d'audit doit **survivre à son référent** :
  c'est l'inverse de ce qu'une FK affirme.
- **Aucun retrait d'affichage** (marqueur d'archivage). Écarté avec l'humain :
  une fois le RPPS libéré par l'US dédiée, une ligne détachée ne gêne plus rien
  — elle n'apparaît que si l'on coche la case.

## Definition of Done

### Le comportement, sur les trois fronts

- [ ] Une ligne dont l'état est **détaché** n'affiche **ni** « Définir par
      défaut » **ni** « Supprimer » — masqués, pas grisés : un bouton grisé
      annonce encore une action (arbitrage humain du 2026-09-15, déjà appliqué
      au « Par défaut » sur `client-mobile`)
- [ ] Elle affiche **« Rattacher »**, qui rattache l'adresse de la ligne par le
      chemin existant — donc **avec la sonde opérateur**, jamais en écrivant
      directement le registre
- [ ] Après un rattachement réussi, la ligne repasse **Active** et retrouve ses
      actions ordinaires, **sans rechargement de page**
- [ ] Une ligne **non détachée** garde exactement ses actions actuelles — c'est
      la contre-épreuve, et elle doit être testée
- [ ] La ligne détachée affiche **« Détachée le {date} »** au lieu de
      « Rattachée le {date} »
- [ ] Les dates sont **formatées** (locale `fr-FR`), plus d'ISO brut

### Le contrat

- [ ] `MailboxDto` porte `DetachedAt` (`DateTimeOffset?`, null si non détachée)
- [ ] `api-mail` le renseigne depuis `RegistryTenant.DetachedAt`
- [ ] Le paquet NuGet `dtos-mss` est publié et les consommateurs .NET bumpés
      (`api-mail`, `client-blazor`)
- [ ] Les modèles TypeScript de `client-angular` et `client-mobile` portent
      `detachedAt?: string`

### Les tests

- [ ] Un test par front : une ligne détachée n'expose **pas** les deux actions,
      et **expose** « Rattacher ». Vérifié **ROUGE** avant correction (rule 1)
- [ ] Un test par front sur la contre-épreuve : une ligne **active** conserve
      ses actions
- [ ] Un test par front : la ligne détachée affiche la date de **détachement**
- [ ] `api-mail` : un test vérifie que `DetachedAt` est renseigné pour une boîte
      détachée et **null** pour une boîte active
- [ ] Build + tests verts sur les cinq repos

### Ce qui ne doit pas bouger

- [ ] Le rattachement passe **toujours** par la sonde opérateur — aucun chemin
      qui écrirait le registre sans elle
- [ ] Le `TenantId` est préservé au re-rattachement (comportement existant de
      `AttachMailboxAsync`) : un test le fige si ce n'est pas déjà le cas

## Manual Test Plan

**Pré-requis** : un praticien avec une messagerie rattachée.
**Lancer** : `cd Api/Mail && aspire run --project src/AppHost`, puis le front.

1. Détacher la messagerie, puis cocher **« Afficher les messageries détachées »**
2. **Attendu** : la ligne détachée n'affiche **que** « Rattacher ». Ni « Définir
   par défaut », ni « Supprimer »
3. **Attendu** : elle indique **« Détachée le »** suivi d'une date lisible, pas
   d'un horodatage ISO
4. Cliquer **« Rattacher »**
5. **Attendu** : la sonde opérateur s'exécute, la ligne repasse **Active** et
   retrouve ses actions, sans rechargement de page
6. **Non-régression** : une messagerie active affiche toujours « Définir par
   défaut » et « Supprimer », et « Rattacher » n'y apparaît pas

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : MSSanté — lisibilité du parcours de gestion des
  adresses ; PGSSI-S § journalisation (conservation de l'imputabilité)
- **INS** : non applicable — aucune identité patient, aucun document
- **Authentification PS** : Pro Santé Connect / e-CPS, eIDAS substantiel —
  **inchangé**. Le rattachement conserve sa sonde XOAUTH2 : la US ne crée aucun
  chemin d'écriture du registre qui contournerait l'opérateur.
- **Habilitations** : RPPS porté par le jeton PSC — contrôle inchangé
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : rattachement et détachement restent journalisés à
  l'identique. **Le point central de cette US est conservatoire** : en retirant
  « Supprimer », elle protège le `TenantId` que les traces référencent. Aucune
  trace n'est retirée, aucune ne devient orpheline. Conservation 6 ans,
  inchangée.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement existant, inchangé
- **AIPD / impact RGPD** : inchangé. Aucune donnée nouvelle : `detached_at`
  existe déjà en base, la US l'expose au praticien qui en est le sujet.
