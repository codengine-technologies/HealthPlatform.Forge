# todo-task-310.md — Supprimer la messagerie ouverte laisse une session IMAP orpheline chez l'opérateur

**Repos**: client-angular, client-blazor, client-mobile
**Dependencies**: **task-303** (mergée — elle a posé la rotation d'identifiant de session
et la fermeture de la session sortante), **task-304** (mergée — elle a livré l'écran de
gestion et sa suppression). Aucune dépendance sortante.
**Epic**: E016
**Priorité**: **2** — rien ne casse à l'écran et aucune donnée n'est en jeu. Mais une
connexion reste ouverte chez l'opérateur MSSanté pour une messagerie que le praticien
croit avoir retirée, et elle s'y lit comme une session fantôme.

## Objective

Fermer la session de messagerie **avant** de détacher la boîte, et non après.

Aujourd'hui l'ordre est inversé : la fermeture part avec les en-têtes d'une boîte qui
vient d'être détachée, le backend la refuse, et le pool IMAP n'est jamais fermé
proprement.

## Le défaut, tracé dans le code

Constaté le 2026-09-14 en répondant à la question « si je supprime la messagerie sur
laquelle je suis connecté, comment le logiciel réagit ? ».

**La séquence actuelle**, identique sur les trois fronts
(`confirmRemove` / `ConfirmRemoveAsync`) :

```
1. DELETE /api/v1/account/mailboxes/{tenantId}   → state = Detached
2. reload de la liste
3. si c'etait la COURANTE → switchTo(repli)
     3a. sessionCloser()   ← POST /api/v1/sync/logout
                             avec Client-Email = la boite QUI VIENT D'ETRE DETACHEE
     3b. purge, nouvel identifiant de session, bascule
```

**L'étape 3a échoue, systématiquement.** `POST /api/v1/sync/logout` ne porte pas
`[MailboxNotRequired]` : le middleware résout `Client-Email` contre le registre, trouve le
rattachement en `Detached`, et `MailboxSelectionService` répond `NotCompatible`
(`MailboxSelectionService.cs:65`). La requête est **refusée avant d'atteindre le
contrôleur**, donc `BackgroundSyncManager.CleanupUserAsync` n'est jamais appelé.

Le front l'avale — c'est du best-effort, et c'est délibéré :

```ts
try { await this.sessionCloser() }
catch (error) {
    console.error('[MailboxSession] Failed to close the outgoing session', error)
}
```

### Ce que ça coûte

Le pool IMAP de la boîte supprimée **reste connecté chez l'opérateur MSSanté** jusqu'à son
propre délai d'expiration. C'est exactement le « pool IMAP orphelin » que la rotation
d'identifiant de session de task-303 existe pour éviter :

> *Le backend lie un `Client-Session-Id` à la première boîte qu'il a ouverte et refuse en
> 409 le même identifiant présenté avec une autre boîte, **précisément pour qu'une bascule
> ne laisse pas un pool IMAP orphelin**.*

La suppression est le **seul** chemin qui le produise, parce que c'est le seul où la boîte
sortante cesse d'être valide **avant** qu'on essaie de la fermer. Une bascule ordinaire ou
une déconnexion ferment toutes deux une boîte encore rattachée, et aboutissent.

> **Ce n'est pas un défaut de sécurité.** La session IMAP orpheline appartient au
> praticien lui-même, elle expire seule, et aucune donnée ne fuit. C'est un défaut de
> **propreté d'exploitation** : elle consomme une connexion chez l'opérateur, et elle se
> lit dans ses journaux comme une session que personne n'a fermée.

## Le correctif — fermer tant que la boîte est encore valide

**Inverser l'ordre** : fermer la session, **puis** détacher.

```
1. si c'est la COURANTE → sessionCloser()    ← la boite est encore Active, l'appel aboutit
2. DELETE /api/v1/account/mailboxes/{tenantId}
3. reload de la liste
4. adopter le repli avec un identifiant de session NEUF
```

### Le piège de l'étape 4 — ne pas fermer deux fois

`switchTo()` appelle **lui-même** le `sessionCloser` (c'est l'étape 2 de sa séquence §D).
L'utiliser à l'étape 4 rejouerait la fermeture sur une boîte désormais détachée, et
reproduirait exactement le défaut qu'on corrige — une deuxième fois, en silence.

Le store expose déjà les primitives nécessaires : `open(mailbox)` pose la boîte courante et
tire un identifiant neuf **sans rien fermer**, et `clear()` purge l'état local. Le chemin
de suppression doit passer par là, ou par une variante explicite de `switchTo` qui sait que
la sortante est **déjà fermée**.

**Ce qu'il ne faut pas faire** : marquer `sync/logout` en `[MailboxNotRequired]`. La route
saurait alors être appelée sans boîte résolue — donc sans savoir **quelle** session IMAP
fermer. On déplacerait le défaut du front vers le backend.

## Definition of Done

### Le comportement, sur les trois fronts

- [ ] Lors de la suppression de la messagerie **courante**, la fermeture de session part
      **avant** l'appel de détachement, et elle **aboutit** (200, pas de refus)
- [ ] La fermeture n'est appelée **qu'une fois** par suppression. Le repli est adopté sans
      rejouer de fermeture sur une boîte détachée
- [ ] Supprimer une messagerie qui **n'est pas** la courante ne déclenche **aucune**
      fermeture de session — le comportement actuel est correct et ne doit pas changer
- [ ] Les trois issues existantes sont préservées : repli sur la boîte par défaut héritée,
      sinon `select` s'il reste une boîte sélectionnable, sinon `onboarding`
- [ ] L'identifiant de session est **neuf** après la suppression de la courante : le
      backend refuse en 409 `SESSION_MAILBOX_MISMATCH` un identifiant présenté avec une
      autre boîte

### Les tests — c'est l'ordre qui est testé, pas seulement le résultat

- [ ] **`client-angular`**, **`client-mobile`**, **`client-blazor`** — un test par front
      vérifie l'**ordre des appels** : fermeture de session **puis** détachement. Un test
      qui se contenterait de vérifier que les deux ont eu lieu passerait aussi sur le code
      défectueux
- [ ] Un test par front vérifie qu'une suppression de boîte **non courante** n'appelle
      **pas** la fermeture
- [ ] Un test par front vérifie que la fermeture n'est appelée **qu'une fois** quand la
      courante est supprimée et qu'un repli existe — c'est la contre-épreuve du piège
      `switchTo`
- [ ] Build + tests verts sur les trois fronts

### Ce qui ne doit pas bouger

- [ ] `POST /api/v1/sync/logout` **reste** sans `[MailboxNotRequired]` — la route doit
      continuer d'exiger une boîte résolue, sans quoi elle ne saurait pas laquelle fermer
- [ ] Aucun changement backend. Le diff se limite aux trois fronts
- [ ] La déconnexion (`MAIL_SESSION_CLOSER`, task-285) et la bascule ordinaire
      (`switchTo`, task-303 §D) sont **inchangées** : leurs tests existants restent verts
      sans modification d'assertion

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`, puis le front à tester.
- **Préparer** : un praticien avec **deux** messageries MSSanté de formation rattachées,
  l'une par défaut.
- **Actions et vérifications** :
  1. Ouvrir la messagerie **non par défaut** (bascule via le sélecteur) — c'est elle qu'on
     va supprimer, pour que le repli soit non trivial.
  2. Aller dans la gestion des messageries, supprimer **celle sur laquelle on est**,
     confirmer.
  3. **Attendu à l'écran** : la bascule s'opère vers la messagerie restante, la boîte de
     réception se recharge dessus. Aucun message d'erreur.
  4. **Attendu dans les journaux serveur (Seq)** : une trace `MailboxSessionClosed` portant
     l'adresse **supprimée**, suivie de `MailboxDetached`, puis `MailboxSessionOpened` sur
     la messagerie de repli. **Dans cet ordre.**
  5. **Attendu dans la console du navigateur** : **aucun** `[MailboxSession] Failed to
     close the outgoing session`. C'est la ligne qui signe le défaut aujourd'hui.
  6. **Contre-épreuve** : supprimer maintenant la messagerie **non courante** → aucune
     trace `MailboxSessionClosed`, la session en cours n'est pas touchée, on reste sur
     place.
  7. **Cas de la dernière** : supprimer la dernière messagerie restante → fermeture tracée,
     puis retour à l'écran d'onboarding.
- **Données de test** : praticien synthétique du realm de formation, deux adresses MSSanté
  de formation. Aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correction de propreté d'exploitation sur un mécanisme
  existant
- **Exigences DSR honorées** : non applicable — aucun échange, aucun document
- **INS** : non applicable — aucun patient manipulé
- **Authentification PS** : inchangée. La suppression exige déjà une session Pro Santé
  Connect active ; cette US ne touche ni la condition ni le contrôle
- **Habilitations** : inchangées — aucune route nouvelle, aucun contrôle d'accès modifié
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **amélioré, et c'est une partie du sujet.** `MailboxSessionClosed`
  est aujourd'hui **absente** du journal quand on supprime la boîte courante, puisque la
  requête qui l'écrit est refusée. La frontière de session est donc incomplète : le journal
  montre une messagerie ouverte que rien ne ferme. Après cette US, toute session ouverte a
  sa fermeture tracée, y compris sur ce chemin. Durée de conservation inchangée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucun flux, aucune donnée déplacée
- **AIPD / impact RGPD** : inchangé. Aucune donnée personnelle nouvelle. La correction
  **réduit** la durée de vie d'une connexion authentifiée chez un tiers, ce qui va dans le
  sens de la minimisation

### DOD santé applicable

- [ ] `MailboxSessionClosed` est journalisée pour **toute** session de boîte ouverte, y
      compris quand la boîte est supprimée pendant qu'elle est ouverte — vérifié dans Seq
      au test manuel
- [ ] Aucune adresse MSSanté n'apparaît dans la console du navigateur ni dans un journal
      front

## Ce que cette US n'est pas

- **Pas un correctif de sécurité.** La session orpheline appartient au praticien lui-même,
  elle expire seule, et aucune donnée ne fuit. C'est de la propreté d'exploitation et de la
  complétude du journal.
- **Pas un assouplissement de `sync/logout`.** La route continue d'exiger une boîte
  résolue. La rendre appelable sans boîte déplacerait le défaut vers le backend, qui ne
  saurait plus quelle session IMAP fermer.
- **Pas une refonte de la séquence de bascule.** `switchTo` (task-303 §D) et la déconnexion
  (task-285) ne bougent pas. Seul le chemin de **suppression** change d'ordre.
- **Pas une correction backend.** Le serveur se comporte correctement : il refuse une
  requête portant une boîte détachée, et il a raison de le faire.
