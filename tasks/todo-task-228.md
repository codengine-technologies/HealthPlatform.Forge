# todo-task-228.md — L'enrichissement tient le verrou de session IMAP jusqu'à 58 s : ouvrir un message attend derrière le lot entier

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-227 (wip, à merger d'abord)** — pose les tests qui
assertent réellement le skip des UIDs déjà enrichis, le lot mixte et la chaîne
bout en bout sur base réelle : c'est le filet anti-régression exact du refactor
de cette task (ne pas refactorer la Phase A tant que ces tests ne sont pas sur
`develop`) ; task-079 (mergée) — a séparé la Phase A (fetch IMAP sous verrou)
de la Phase B (persistance hors verrou) : cette task découpe la Phase A elle-même ;
task-211 (mergée) — instrumentation des trois verrous, indispensable à la
contre-épreuve ; task-213/214 (archivées) — leçon de méthode : tout correctif de
verrou se **prouve par un tir avant/après en iso-conditions**, jamais par
intuition (la voie d'écriture de task-213 a été retirée après contre-épreuve).
**Priorité**: **1** — c'est le goulet structurel désigné par le tir
journey-mssante-n300 du 2026-08-04 : il dégrade **trois gestes du médecin à la
fois** (ouvrir un message, rafraîchir l'inbox, marquer lu).

## Objective

Qu'aucun geste court du médecin (ouvrir un message, lister un dossier, marquer
lu) n'attende plusieurs secondes derrière un **lot d'enrichissement entier** de
sa propre session. Aujourd'hui, `EnrichEmailsAsync` acquiert le verrou
`imap_session` **une fois pour tout le lot** et le garde pendant toute la
Phase A (fetch réseau des corps + pièces jointes de chaque message, en
séquentiel, sous latence MSSanté) : détention p95 mesurée à **58,5 s**.

La US demande de **découper la Phase A en sous-lots** : acquérir le verrou,
fetcher un sous-lot de messages, relâcher le verrou, et laisser les opérations
courtes de la même session s'intercaler avant le sous-lot suivant. La taille de
sous-lot est un paramètre de configuration avec une valeur par défaut
raisonnable (ordre de grandeur 10–20 UIDs — à faire trancher par la mesure,
pas par le goût).

**US backend-only (justification)** : portée d'un verrou applicatif dans
`ImapService.EnrichEmailsAsync` (Phase A). Aucun contrat DTO, aucun écran,
aucun changement de comportement fonctionnel visible — seulement l'ordonnancement
interne des opérations IMAP d'une session.

## La mesure — tir `journey-mssante-n300` du 2026-08-04

Rapport : `Api/Mail/tests/loadtest-k6/reports/2026-08-04/report-journey-mssante-n300-142603.md`
(300 médecins, modèle fermé, K=1,2, latence mssante injectée).

| Verrou / opération | Attente p95 | **Détention p95** | Acquisitions/s |
|---|---|---|---|
| `imap_session` (global) | 0,765 s | **58,500 s** | 52,84 |
| `imap_session` / `EnrichEmails` | 0,005 s | **58,500 s** | 2,80 |
| `imap_session` / `GetEmailContent` | **1,790 s** | 2,112 s | 17,84 |

**Lecture.** La détention du verrou de session est entièrement portée par
`EnrichEmails` : le fetch réseau du lot complet se fait sous le verrou
(Phase A), et c'est `GetEmailContent` — le geste du médecin qui ouvre un
message — qui paie l'attente (1,79 s au p95, 17,8 acquisitions/s). Les max
aberrants du tir (`read_list` 15,1 s, `read_content` 7,4 s, `mark_read` 7,4 s)
sont cohérents avec un geste coincé derrière un lot d'enrichissement.

La cause est confirmée dans le code : depuis task-079 la persistance (Phase B)
est bien hors verrou, mais la Phase A garde le verrou pendant **toute** la
boucle de fetch des messages du lot.

## Contraintes — ce que le découpage ne doit pas casser

1. **La garantie anti-course de la clé de verrou.** La clé actuelle
   (`EnrichEmails:{folder}:{pendingUidsHash}`) sérialise deux passes
   d'enrichissement concurrentes sur le **même** jeu de UIDs, précisément pour
   éviter la course sur l'upsert par UID (`DbUpdateConcurrencyException` vue en
   Seq avant ce correctif — commentaire en tête de la méthode). Relâcher le
   verrou entre deux sous-lots rouvre potentiellement cette fenêtre : le
   découpage doit préserver l'exclusion entre passes concurrentes sur les mêmes
   UIDs (par exemple en conservant une sérialisation au niveau du lot logique,
   tout en relâchant la session IMAP entre sous-lots). C'est le point dur de la
   US — s'il s'avère irréductible, ouvrir `questions/task-228.md` plutôt que
   d'affaiblir la garantie.
2. **La complétude de l'enrichissement.** Un lot interrompu entre deux
   sous-lots (annulation, erreur IMAP) doit laisser le système dans l'état déjà
   toléré aujourd'hui : les UIDs non traités restent « pending » et sont repris
   à la passe suivante. Aucun message perdu, aucun message enrichi deux fois
   avec des contenus divergents.
3. **Le coût total de l'enrichissement.** Relâcher/réacquérir le verrou et
   rouvrir le dossier IMAP à chaque sous-lot a un coût (aller-retour sous
   latence MSSanté). La durée totale d'enrichissement d'un lot ne doit pas se
   dégrader au-delà de ce que la contre-épreuve juge acceptable (< +20 % sur la
   durée de bout en bout d'un lot, à confirmer au tir).
4. **La télémétrie existante.** Les compteurs de verrous (task-211) et les
   activités OTLP doivent continuer de mesurer chaque acquisition — c'est eux
   qui rendent la contre-épreuve possible.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] La Phase A d'`EnrichEmailsAsync` fetch par sous-lots, verrou `imap_session` relâché entre chaque sous-lot
- [ ] Taille de sous-lot configurable (options .NET), valeur par défaut documentée dans le code
- [ ] La garantie anti-course entre passes concurrentes sur les mêmes UIDs est préservée (contrainte 1) — test unitaire qui le prouve
- [ ] Unit tests du découpage : lot < taille de sous-lot (1 seul sous-lot), lot multiple, annulation entre deux sous-lots (reprise propre), erreur IMAP au milieu (UIDs restants toujours pending)
- [ ] Aucune régression sur les tests d'enrichissement existants
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté) — les logs de sous-lots ne loggent que folder + compte d'UIDs
- [ ] **Contre-épreuve au banc (bloquante pour le merge, pas pour la PR)** : tir `journey` n300 en iso-conditions (même K, même seed, reset-state, même lignée de code à la task près) avant/après, et dans le rapport « après » :
  - détention p95 `imap_session` / `EnrichEmails` **très nettement réduite** (ordre de grandeur attendu : ≤ 10 s)
  - attente p95 `imap_session` / `GetEmailContent` **en nette baisse** (référence : 1,79 s)
  - durée de bout en bout d'un lot d'enrichissement non dégradée au-delà de +20 %
  - vérification par base toujours PASS (propriété + complétude), zéro `DbUpdateConcurrencyException` en Seq

## Manual Test Plan

- Monter le banc : suivre le skill `loadtest-skill` (AppHost profil `loadtest`,
  GreenMail/Dovecot + Toxiproxy, seed des boîtes)
- Tir de contre-épreuve : `journey`, 300 médecins, latence `mssante`, K=1,2,
  iso-conditions avec le tir de référence `journey-mssante-n300-142603`
  (reset-state avant tir — la bande froide recouvre la bande enrich)
- Ouvrir le rapport généré dans `Api/Mail/tests/loadtest-k6/reports/{date}/`
- Comparer la table « Verrou de session `imap_session`, par opération » au
  rapport de référence du 2026-08-04 : détention `EnrichEmails` et attente
  `GetEmailContent` doivent avoir chuté dans les proportions du DOD
- Vérifier « Vérification par base » : PASS, 0 sujet étranger, complétude tenue
- Vérifier en Seq (MCP seq-local) : aucune `DbUpdateConcurrencyException`,
  aucun nouveau warning d'enrichissement hors bruit connu
- Contrôle fonctionnel rapide : ouvrir l'inbox d'un praticien de test pendant
  qu'un enrichissement tourne — l'ouverture d'un message ne doit plus se figer
  plusieurs secondes

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — optimisation de performance interne, aucune exigence DSR nouvelle honorée ni retirée
- **Exigences DSR honorées** : non applicable — pas de changement de périmètre fonctionnel
- **INS** : non applicable — aucun traitement d'identité modifié ; l'enrichissement CDA en aval (Phase B) est inchangé
- **Authentification PS** : inchangée — la US ne touche pas au flux d'authentification (PSC/e-CPS)
- **Habilitations** : non applicable — aucune règle d'accès modifiée
- **Interop CI-SIS** : non applicable — le parsing CDA (`interop-cda`) et son ordonnancement Phase B sont hors périmètre
- **Tracé PGSSI-S** : inchangé — les évènements existants (enrichissement, accès messagerie) restent journalisés ; les nouveaux logs de sous-lots ne portent que folder + compte d'UIDs, jamais de contenu
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucun flux ni stockage nouveau
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau, aucune donnée nouvelle
