# todo-task-153.md — « Répondre à tous » (Angular + mobile)

**Repos**: client-angular, client-mobile
**Dependencies**: —
**Epic**: E009

## Objective

Ajouter **« Répondre à tous »** aux deux clients : l'analyse différentielle
(2026-07-05) a montré que la fonction manque **à la fois** dans
`client-angular` (`mail-detail.component.ts` — `reply()` ne pré-remplit que
l'expéditeur) et dans `client-mobile`. C'est un manque commun, pas un écart de
parité — d'où une US bi-repo (branche unique `feat/task-153-...` sur les deux).

Comportement attendu (standard messagerie) :
- **À** = expéditeur d'origine (`Reply-To` s'il existe, sinon `From`)
- **+ À** = tous les destinataires `To` d'origine **moins l'adresse de la
  boîte du praticien** (pas d'auto-adressage)
- **Cc** = les `Cc` d'origine, moins l'adresse du praticien
- Aucun destinataire `Cci` repris (jamais divulgué)
- S'il ne reste qu'un destinataire après filtrage → résultat identique à
  « Répondre » (pas de doublon d'action gênant, mais l'action reste proposée)
- Citation, objet « Re: » et threading RFC-5322 identiques au « Répondre »
  existant (réutiliser la mécanique en place, y compris
  `rfc5322-threading.utils.ts` côté Angular)

Surface UI :
- **Angular** : bouton/entrée « Répondre à tous » dans la toolbar du détail, à
  côté de « Répondre »
- **Mobile** : entrée « Répondre à tous » dans les actions du détail (à côté
  de Répondre/Transférer)
- L'action n'apparaît que si le mail d'origine a **plus d'un correspondant**
  après filtrage (sinon seule « Répondre » est montrée) — même règle sur les
  deux clients

US **frontend-only** : l'envoi passe par `sendMail` existant. Aucun changement
backend ni DTO. La logique de calcul des destinataires est **pure** et testée
unitairement sur chaque client (util partagé conceptuellement : même
spécification, deux implémentations TS).

## Definition of Done

- [ ] Build passe sur les deux repos (Angular : `npm ci && npm run build` ; mobile : idem) — 0 erreur
- [ ] Tests passent sur les deux repos — 0 échec
- [ ] Util pur de calcul des destinataires (par client) + tests : Reply-To prioritaire, exclusion de sa propre adresse (To et Cc), exclusion des Cci, casse/espaces normalisés, mail mono-correspondant
- [ ] Angular : « Répondre à tous » dans la toolbar détail, visible seulement si > 1 correspondant
- [ ] Mobile : entrée équivalente dans les actions du détail, même règle de visibilité
- [ ] Compose pré-rempli : À/Cc corrects, citation + « Re: » + threading identiques à « Répondre »
- [ ] Aucun auto-adressage (l'adresse du praticien n'apparaît jamais dans les destinataires pré-remplis)
- [ ] Libellés FR en dur ; `data-testid` sur la nouvelle action (deux clients)
- [ ] Angular : lint scope MSS propre (`--projects=tag:scope:mss`)

## Manual Test Plan

- Boîte de test avec un mail reçu ayant : From = confrère A, To = moi + confrère B, Cc = confrère C
- **Angular** (`cd Client/Angular/front && npm start`) : ouvrir le mail → « Répondre à tous » → À = A + B, Cc = C, moi absent ; envoyer → thread conservé
- **Mobile** (`cd Client/Mobile && npm start`) : même scénario, mêmes destinataires pré-remplis
- Mail avec un seul correspondant (From = A, To = moi) → « Répondre à tous » absent, « Répondre » seul
- Mail avec Reply-To ≠ From → « Répondre à tous » cible le Reply-To
- Vérifier qu'aucun Cci d'origine n'est repris

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — complément d'une capacité d'émission déjà référencée
- **Exigences DSR honorées** : non applicable — en-têtes MSSanté et libellé expéditeur inchangés (générés à l'envoi par le backend, tasks 001/009)
- **INS** : non applicable
- **Authentification PS** : session existante ; l'envoi MSSanté reste sous authentification forte
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — pas de nouveau format
- **Tracé PGSSI-S** : envoi journalisé côté `api-mail` (canal existant)
- **Consentement patient** : point d'attention — si un destinataire d'origine est un patient MES, les garde-fous d'envoi existants (opposition, blocage réponse) s'appliquent au compose pré-rempli comme à tout envoi ; aucune règle nouvelle
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — backend existant
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : feat/task-153-reply-all (commit f3fa925)
- `client-angular` (code-only) : code écrit sur la branche courante `feature/nova-rewriting-mss`, **non commité** — l'humain gère commit/push/PR TFS. Fichiers :
  - `front/libs/mss/src/core/utils/reply-all-recipients.util.ts` (+ .spec.ts)
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.{ts,html,spec.ts}`

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/55 — label `awaiting-human-merge`
- `client-angular` : aucune PR forge (code-only, TFS). Validé MSS-scoped : nx test mss-lib 312 OK, nx lint mss-lib 0 erreur.

## Staging
- Mobile agrégée dans `forge/staging-task-142-160-20260716` ; 674 tests verts.
- **CONFLIT D'INTÉGRATION résolu** : task-152 (#54) et task-153 (#55) ajoutent toutes deux un champ `to?` à `ComposeRequest` avec des types incompatibles (`string[]` vs `MailAddressDto[]`). Réconcilié dans staging en renommant le champ string[] de task-152 en `toEmails` (mail-event.service + mail-compose + ai-chat + spec). **⚠️ À appliquer au merge de #54+#55 sur develop** (sinon collision de type).

## Code Review Summary
- APPROVED (2 repos). Logique pure testée identiquement, réutilisation reply/threading, pas d'auto-adressage, FR en dur, data-testid. Mobile build 0 erreur / 522 tests ; Angular MSS 312 tests / lint clean.

## Merged
- 2026-07-17 — squash-merge sur `develop` (conflit sémantique ComposeRequest.to → réconcilié `toEmails`/`to`/`cc`, consommateurs renommés ; spec union)
- `client-mobile` : 6211ecb (PR #55 fermée)
- `client-angular` : géré manuellement par l'humain (code-only TFS)
