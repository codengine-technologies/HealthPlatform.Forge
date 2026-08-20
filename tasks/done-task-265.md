# todo-task-265.md — Un placeholder de fusion resté dans un mail fait tomber le résumé en erreur 500 : le corps d'un message n'est pas du code

**Repos**: api-mail
**Epic**: E009
**Single frontend**: true
**Dependencies**: aucune.
**Priorité**: **1** — le défaut est **déclenché par la donnée reçue**, donc
reproductible à volonté par n'importe quel expéditeur MSSanté, et il tombe sur
**le geste le plus visible du médecin** : demander le résumé d'un message.

## Objective

Qu'un message reçu ne puisse jamais faire échouer son propre résumé à cause de
ce qu'il contient. Le corps d'un mail est une **donnée à analyser**, pas des
instructions à exécuter.

## Ce qui est établi — Seq, 2026-08-17 16:03:14 UTC

Constaté depuis le front `client-angular`, boîte
`virginie.medecinrpps0062267@medecin.formation.mssante.fr`, trace
`372649854f6aa1e4aa22874599ae9495`, corrélation `09a0706c` :

```
❌ Unhandled exception - GET /api/v1/mail/folders/INBOX/emails/summary/4891
HTTP GET … - Status=500, ElapsedMs=87459, Size=0

System.Collections.Generic.KeyNotFoundException:
  The plugin collection does not contain a plugin and/or function
  with the specified names. Plugin name - '', function name - 'SenderTitle'.
   at Microsoft.SemanticKernel.KernelPromptTemplate.RenderAsync(...)
   at EmailSummaryService.GenerateSummaryFromAiAsync(...) EmailSummaryService.cs:188
   at EmailSummaryService.ProcessSingleEmailAsync(...) :120
   at MailController.GetEmailSummaryAsync(...) MailController.cs:424
```

**La même exception, 1 min 27 plus tôt, sur un second chemin** : trace
`04dc51917e3352d80b690f6c4144adfe`, `Operation=ProcessNewMail`,
`EmailTaggingService.SuggestTagsAsync` (`EmailTaggingService.cs:51`) — mais là
elle est **avalée** par le `catch (Exception)` (« Failed to suggest tags » →
retourne `[]`). Même message, deux services, deux comportements : une erreur
500 pour le médecin d'un côté, un mail **silencieusement non étiqueté** de
l'autre.

### La cause, et pourquoi elle est certaine

`kernel.InvokePromptAsync(prompt)` ne reçoit pas une chaîne littérale : Semantic
Kernel traite l'argument comme un **gabarit**, où `{{…}}` est du code (appel de
fonction de plugin). Or le prompt est fabriqué par simple interpolation, corps
du mail collé dedans — `AiPromptHelper.cs:37` :

```csharp
return $"{Promt.ALL}\n{typePrompt}\n{Promt.DONOT}\nHere is the document to analyze:\n{content}";
```

Le message UID 4891 porte donc dans son corps un littéral **`{{SenderTitle}}`**
— un placeholder de fusion que le logiciel émetteur n'a pas substitué. SK le
parse comme `plugin '' / fonction 'SenderTitle'`, ne le trouve pas (le kernel
n'enregistre **aucun plugin** : `SemanticKernelExtensions.cs:86-105` ne branche
que la complétion de chat et les embeddings) et lève `KeyNotFoundException`.

Deux faits verrouillent ce diagnostic :

1. **`SenderTitle` n'existe nulle part dans le code** — 0 occurrence sur `src/`
   et `tests/`, gabarits `Ressources/Prompts/*.txt` inclus (aucun de ces
   fichiers ne contient `{{`). La chaîne ne peut venir que du contenu runtime.
2. **Le prompt du résumé n'interpole que le contenu du message** (`ALL` + prompt
   de type + `DONOT` + corps) : ni expéditeur, ni sujet, ni métadonnée. Le
   `{{SenderTitle}}` est donc **dans le corps**, pas dans un en-tête.
   Seq le confirme par les tailles : `Original content: 525 chars` →
   `prompt length: 3403 characters`.

### Ce que ça pèse, et ce que ça ouvre

Sur 7 jours, **3** réponses 500 sur cet endpoint : celle-ci, et deux le
2026-05-17 sur l'UID 4416 en 1,8 s (autre cause, hors scope). Le défaut n'est
donc **pas** systémique en volume — il est **systémique en nature** : tout
message contenant `{{…}}` le déclenche, et un expéditeur peut le provoquer.

Au-delà du plantage, c'est une **primitive d'injection de gabarit** : le corps
d'un message atteint le moteur de gabarit du kernel. Aujourd'hui elle ne fait
que planter parce qu'aucun plugin n'est enregistré. Le jour où un plugin l'est,
un expéditeur pourra déclencher l'appel d'une fonction du kernel depuis le corps
d'un mail. Le corriger maintenant coûte quatre lignes ; plus tard, ce sera une
faille.

### Les quatre sites d'appel exposés

| Site | Contenu non maîtrisé interpolé | Comportement aujourd'hui |
|---|---|---|
| `EmailSummaryService.cs:188` | corps du mail / documents CDA | **500 au médecin** |
| `EmailTaggingService.cs:51` | corps + `senderEmail` | silencieux, mail non étiqueté |
| `AiConversationService.cs:460` | digests des mails sélectionnés | dégradé (message de repli) |
| `AiConversationService.cs:531` | message du médecin + réponse IA | dégradé |

## Ce qu'il ne faut PAS présumer

- **Ce n'est pas un incident OpenAI, ni un timeout, ni une panne réseau.**
  L'exception est levée **au rendu du gabarit**, avant tout appel HTTP au
  fournisseur. Aucun token n'a été consommé.
- **Ce n'est pas un mail malformé au sens MIME.** Le message est parfaitement
  valide ; son corps contient juste deux accolades.
- **Ce n'est pas propre au type de document.** Le contenu fait 525 caractères
  (corps simple, pas de document CDA) : le chemin CDA est exposé exactement de
  la même façon, puisqu'il alimente le même `content`.
- **Échapper les accolades dans le contenu n'est pas la bonne réponse.**
  Neutraliser par remplacement de caractères abîme la donnée analysée (le
  modèle ne verra plus le texte réel) et laisse le contenu dans le gabarit.
  La donnée non maîtrisée doit **sortir** du gabarit.
- **Le `catch (Exception)` d'`EmailTaggingService` n'est pas un correctif** —
  c'est ce qui a rendu le défaut invisible pendant qu'il se produisait.

## Ce que la US doit livrer

1. **Le contenu non maîtrisé passe en argument, plus jamais dans le gabarit.**
   Sur les quatre sites : le gabarit ne porte qu'un **nom de variable**, la
   valeur est fournie via `KernelArguments`. Semantic Kernel insère la valeur
   d'une variable **verbatim**, sans la re-parser — c'est ce qui ferme le
   défaut. Piège d'écriture à connaître : dans une chaîne interpolée `$"…"`,
   `{{` produit `{` — il faut donc construire le gabarit par concaténation ou
   littéral brut, sinon le nom de variable est détruit à la compilation.
2. **Le résumé ne rend plus 500 sur une condition de donnée.** Un message non
   résumable est un cas métier, pas une panne serveur : renvoyer un résumé vide
   comme le fait déjà le chemin « contenu non extractible »
   (`EmailSummaryService.cs:107-117`), ou un `ProblemDetails` typé (règle 12,
   jamais un `StatusCode(500, …)` ad hoc). L'écran du médecin doit afficher un
   message intelligible, pas une erreur technique.
3. **Le tagging cesse d'échouer en silence.** Le `catch` reste (best-effort
   assumé), mais l'échec doit être **compté** — un compteur ou un log de niveau
   Warning attribuable, pour qu'un mail non étiqueté soit constatable sans
   relire Seq à la main.
4. **Un garde-fou de non-régression.** Un test qui échoue si un futur appel
   remet du contenu non maîtrisé dans un gabarit — la forme la plus simple est
   un test qui balaie les appels à `InvokePromptAsync` du projet et exige la
   forme « gabarit + arguments ».

### Hors scope, explicitement

- Les 87 s écoulées avant que le 500 ne parte. L'exception est levée au rendu du
  gabarit, à +50 ms du début de requête d'après Seq ; la stack n'explique pas le
  délai. L'hypothèse la plus simple est une **pause first-chance du débogueur**
  (`ASPNETCORE_ENVIRONMENT=Development`, session de mise au point en cours).
  À écarter en rejouant l'appel **hors débogueur** : si les 87 s persistent,
  c'est un second défaut et il fera l'objet de sa propre US. **Ne pas mélanger
  les deux dans cette task.**
- La refonte du `catch (Exception)` d'`AiConversationService` (chemins déjà
  dégradés proprement).
- L'envoi de contenu clinique à OpenAI, qui est la posture existante du produit
  et non une introduction de cette US (voir section Conformité).

## Definition of Done

- [ ] Build passe (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreur)
- [ ] Tests passent (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échec — hors 3 rouges pré-existants connus)
- [ ] Les 4 sites (`EmailSummaryService.cs:188`, `EmailTaggingService.cs:51`, `AiConversationService.cs:460` et `:531`) passent le contenu non maîtrisé via `KernelArguments` ; aucun ne concatène de contenu reçu dans le gabarit
- [ ] Test unitaire résumé : un corps contenant `{{SenderTitle}}` produit un résumé, sans exception
- [ ] Test unitaire résumé : idem pour `{{$variable}}`, `{{ 'littéral' }}` et `{{plugin.fonction}}` (4 cas, un par forme de syntaxe SK)
- [ ] Test unitaire tagging : un corps contenant `{{Foo}}` ne lève pas et retourne une liste (vide acceptée)
- [ ] Test unitaire tagging : un `senderEmail` contenant `{{Foo}}` ne lève pas
- [ ] Test d'intégration endpoint (règle 1b) : `GET /api/v1/mail/folders/{folder}/emails/summary/{uid}` sur une fixture dont le corps porte `{{SenderTitle}}` → **pas de 500**
- [ ] Aucun `catch` élargi ni `StatusCode(500, …)` ad hoc ajouté — la gestion d'erreur reste au `GlobalExceptionHandler` (règle 12)
- [ ] Un échec de tagging est constatable (compteur ou log Warning attribuable) — plus de retour `[]` muet
- [ ] Garde-fou de non-régression en place : un nouvel appel `InvokePromptAsync` avec contenu interpolé fait échouer un test
- [ ] Aucune donnée de santé en clair dans les logs : ni le prompt, ni le corps du message, ni l'extrait fautif ne sont journalisés (seuls le nombre d'occurrences neutralisées et l'UID sont autorisés)
- [ ] Quality Gate Sonar non dégradée sur le new code

## Manual Test Plan

1. Démarrer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Démarrer le front legacy : `cd Client/Angular/front && npm start`
3. Se connecter avec la boîte de test `virginie.medecinrpps0062267@medecin.formation.mssante.fr`
4. Ouvrir la boîte de réception, sélectionner **le message UID 4891** (celui dont le corps porte le placeholder `{{SenderTitle}}` — c'est la donnée qui a produit l'incident du 2026-08-17)
5. Demander le résumé du message
6. **Attendu** : un résumé s'affiche. À défaut de résumé exploitable, un message métier intelligible (« résumé indisponible pour ce message »), **jamais** une erreur technique ni un écran en erreur
7. Dans Seq (`mcp seq-local`), filtrer `RequestPath like '%/emails/summary/4891'` : **aucun** `@Level = 'Error'`, aucune `KeyNotFoundException`
8. Vérifier que le message porte bien ses étiquettes de priorité (le chemin tagging ne doit plus échouer sur ce mail)
9. Contre-épreuve : s'envoyer un message dont le corps contient `Bonjour {{SenderTitle}}, voici {{$patient}} et {{ 'test' }}`, puis répéter les étapes 5 à 8

**Donnée de test** : boîte de formation MSSanté, aucun patient réel, aucun INS.
Le message UID 4891 existe déjà dans `INBOX` — ne pas le supprimer avant
validation.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — correctif de robustesse sur le couloir MSSanté existant, pas une nouvelle exigence
- **Exigences DSR honorées** : MSSanté — robustesse du traitement d'un message reçu quel qu'en soit le contenu ; aucune exigence DSR nouvelle
- **INS** : non applicable — le résumé ne manipule ni ne dérive l'INS ; le correctif ne touche pas l'identité patient
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel — inchangé, hors scope du correctif
- **Habilitations** : inchangées — le résumé reste réservé au titulaire de la boîte
- **Interop CI-SIS** : CDA r2 en lecture (le contenu résumé peut provenir d'un document CDA via `interop-cda`) — aucun changement de format, aucun contrat modifié
- **Tracé PGSSI-S** : échec de résumé et échec de tagging à journaliser (UID + folder + cause technique **sans contenu**) ; conservation selon la politique existante des journaux applicatifs
- **Consentement patient** : non applicable — aucun partage ni alimentation DMP/Mon Espace Santé
- **Référentiels métier** : LOINC (typage du document CDA en amont du résumé) — inchangé
- **Hébergement HDS** : oui — environnement de développement pour la mise au point, cible HDS inchangée
- **AIPD / impact RGPD** : inchangé — le correctif **réduit** la surface (le corps d'un message ne peut plus atteindre le moteur de gabarit du kernel). **Point de vigilance signalé, non introduit par cette US** : le résumé et le tagging transmettent déjà du contenu clinique à OpenAI ; cette posture relève d'une décision produit distincte et n'est ni aggravée ni traitée ici.

## Arbitrages pris

- **EPIC = E009** (messagerie sécurisée santé), pas E015. Le défaut porte sur
  une fonction produit utilisée par le médecin — le résumé d'un message reçu —
  et non sur le banc de charge. E015 reste l'EPIC du banc.
- **`Repos` = `api-mail` seul.** Aucun contrat ne bouge : le front continue
  d'appeler le même endpoint avec le même schéma de réponse. Si le point 2
  (plus de 500 sur condition de donnée) débouche sur un `ProblemDetails` 422
  plutôt qu'un résumé vide, l'affichage côté `client-angular` /
  `client-blazor` / `client-mobile` devra suivre — **à traiter en US séparée**,
  après arbitrage du comportement retenu.

## Branches

- `api-mail` (pushed) : fix/task-265-contenu-hors-gabarit — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-265-contenu-hors-gabarit
- `dtos-mss` (pushed, auto-inclus) : fix/task-265-contenu-hors-gabarit — aucune modification attendue (aucun contrat ne bouge, cf. « Arbitrages pris »)

Préfixe `fix/` : correctif de robustesse sur un défaut déclenché par la donnée reçue.

## Develop log (2026-08-20)

**Le remède est celui prescrit** (contenu en `KernelArguments`), mais son
réglage a été **établi empiriquement sur SK 1.77**, pas supposé — trois faits
mesurés par sonde jetable avant d'écrire une ligne de correctif :

1. **La valeur d'une variable n'est jamais re-parsée.** `{{SenderTitle}}` y
   survit en texte, dans les deux modes. C'est ce qui ferme le défaut.
2. **Le mode par défaut ENCODE en HTML.** `K+ < 4 & > 2` arrive au modèle en
   `K+ &lt; 4 &amp; &gt; 2`. Sur des bornes de référence cliniques, c'est
   exactement la dénaturation que la US refuse (« le modèle ne verra plus le
   texte réel ») → `AllowDangerouslySetContent` sur les variables, pour une
   insertion **verbatim**.
3. **Le drapeau ne rouvre pas d'injection de rôle dans notre forme.** Une balise
   `<message role="system">` venue du contenu n'est interprétée **que si le
   gabarit lui-même est du XML de chat** : avec un gabarit de chat elle crée un
   vrai message système, avec un gabarit en **texte brut** (le nôtre) elle reste
   inerte. `UntrustedPrompt.Invoke` **refuse** un gabarit de chat pour que
   l'invariant ne puisse pas être perdu par une évolution ultérieure.

Livré (`18c43ee`) : `UntrustedPrompt` (point de passage unique) ;
`AiPromptHelper.GetPrompt` → `GetPromptTemplate` (marque de variable assemblée
par **concaténation** — le piège d'écriture signalé par la US était réel) ;
les 4 sites basculés (`EmailSummaryService`, `EmailTaggingService`,
`AiConversationService` ×2) ; compteur `mssante_tagging_failures_total`
(cause en littéral, zéro donnée de santé) + log Warning attribuable.

**Point DOD affiné en cours de route** : sur la cause `prompt_template`,
l'exception n'est **pas** journalisée — le message d'un `KeyNotFoundException`
de rendu **cite le fragment fautif** (« function name - 'SenderTitle' »), donc
un extrait du corps du mail. Journaliser `ex` aurait fait sortir du contenu de
message par la porte de derrière, contre le DOD « aucune donnée de santé en
clair dans les logs ». Test dédié, mutation vérifiée.

**Aucun `catch` élargi, aucun `StatusCode(500, …)` ajouté** : le correctif
supprime la cause, il ne rattrape pas le symptôme. La gestion d'erreur reste au
`GlobalExceptionHandler` (règle 12).

### Tests — chacun mutation-vérifié

| Garde-fou | Mutation appliquée | Verdict |
|---|---|---|
| 4 syntaxes SK sur le résumé | concaténation restaurée | **rouge**, avec l'exception de production **au mot près** : `Plugin name - '', function name - 'SenderTitle'` |
| Corps + expéditeur sur le tagging | idem | **rouge** — et le modèle n'était **jamais atteint** (`Calls` vide), ce que le `catch` masquait |
| Endpoint `GET …/emails/summary/{uid}` | idem | **rouge** sur 2 cas /4 ; les 2 autres (`{{$patient}}`, `{{ 'test' }}`) ne plantent pas mais **altèrent silencieusement le contenu** — rattrapés au niveau unitaire par l'assertion « verbatim » |
| Balayage anti-`InvokePromptAsync` | appel réintroduit | **rouge**, fichier nommé |
| Non-journalisation de l'exception | `ex` repassé au logger | **rouge** |

Le test d'endpoint rejoue la chaîne réelle de l'incident
(`MailController` → `EmailSummaryService` → `Kernel`) avec le **vrai** service
et un **vrai** kernel ; seules IMAP et le fournisseur de complétion sont
doublés — donc il tourne aussi en CI, sans infrastructure.

### État des suites (exécution **en place**, comme la CI)

| Projet | Résultat |
|---|---|
| `mss.mail.api.tests` | **665 / 665** ✅ |
| `mss.mail.application.tests` | **2 160 / 2 160** ✅ |
| `mss.mail.domain.tests` | **136 / 136** ✅ |
| `mss.mail.infrastructure.tests` | 463 / 464 — **flaky pré-existant** (voir ci-dessous) |
| `mss.mail.integration.tests` | 91 échecs — **identique à la baseline develop** (91/285/42/418), dépendances IMAP/Postgres absentes |

**Deux pièges de mesure rencontrés, à ne pas reproduire :**

- **`--artifacts-path` fait échouer 6 tests d'architecture** (`TrackedSourceScan.RepoRoot()`
  renvoie `null`) : ils remontent depuis le répertoire de sortie pour trouver la
  racine du dépôt, et le drapeau la met hors du dépôt. Ce ne sont **pas** des
  régressions. Le garde-fou de cette task s'ancre volontairement sur
  `[CallerFilePath]` pour être immunisé.
- **`MailReadObjectCountTests.GetMailsByUidsOnAnEmptyPagePublishesAMeasuredZeroAsync`
  est flaky** : vert en isolation, alterne en suite complète. Mesuré **sur
  develop aussi** (2 verts / 2 rouges sur 4 exécutions) — pré-existant, sans
  rapport avec cette task. À ajouter à la liste des rouges connus.

**Rouge pré-existant corrigé au passage** :
`AiPromptHelperTests.GetPromptShouldContainDocumentIntroduction` cherchait
« Voici le document à analyser », chaîne **absente de toutes les ressources** —
le test était rouge sur develop (vérifié par `git stash`). Il assertait une
introduction qui n'existe pas ; il asserte désormais celle qui existe.

**Reste à la main de l'humain (Manual Test Plan)** : la vérification sur l'UID
4891 réel via le front et Seq. Le banc automatisé ne peut pas la produire — elle
porte sur une boîte MSSanté de formation.

## Simplify log (2026-08-20)

Passe qualité sur `api-mail` (seul repo touché) — `d145567`. Cinq axes,
aucun changement de comportement :

- **Altitude** — la grille de priorités du tagging est une **constante de
  code** : elle sort du canal `KernelArguments`, réservé aux **données non
  maîtrisées**, et rejoint le gabarit par concaténation de consts (résolue à
  la compilation). Faire transiter du code par le canal des données brouillait
  l'invariant même que le garde-fou protège.
- **Efficacité** — `EmailSummaryService` calculait la longueur du prompt deux
  fois dans le même appel de log.
- **Simplification** — assertion dupliquée retirée du test d'injection ;
  paramètre `out` supprimé du test d'endpoint (il n'alimentait qu'un
  `Assert.NotNull` sur un objet tout juste construit) ; double de capture passé
  en constructeur primaire, comme le reste du projet.

Re-validation : build 0 erreur ; api **665/665**, application **2160/2160**,
domain **136/136** ; infrastructure 462/464 = le flaky pré-existant caractérisé
au Develop log. `dtos-mss` non touché (et hors périmètre — porteur de contrat).

## Sonar log (2026-08-20)

Analyse complète exécutée sur la branche (`dotnet-sonarscanner`, projet
`healthplatform`, conteneurs redémarrés — ils étaient arrêtés).

### KPIs qualité — baseline → final

| Condition | Baseline | Final | Seuil | Verdict |
|---|---|---|---|---|
| `new_coverage` | 88,0 % | **88,3 %** | ≥ 80 | ✅ (en hausse) |
| `new_duplicated_lines_density` | 0,061 % | **0,058 %** | ≤ 3 | ✅ |
| `new_security_hotspots_reviewed` | 100 % | **100 %** | 100 | ✅ |
| `new_violations` | 59 | **68** | 0 | ❌ |
| **Quality Gate** | **ERROR** | **ERROR** | — | inchangé |

### Le point qui compte : **task-265 contribue 0 violation**

Deux issues avaient été introduites par la task, elles ont été corrigées
(`8eab7a5`) :

- `S103` — la ligne de log du chemin `prompt_template` faisait 166 caractères ;
- `SYSLIB1045` — le balayage anti-gabarit-de-chat passe désormais par
  `[GeneratedRegex]` au lieu d'un `Regex.IsMatch` interprété à chaque fichier.
  **Mutation revérifiée après ce changement de mécanisme** : un gabarit de chat
  introduit dans `EmailSummaryService` fait toujours échouer le garde-fou.

Après correction, la requête d'attribution par fichier renvoie **0 issue** sur
les 11 fichiers de la task, sur les 68 restantes.

### Pourquoi la QG reste ERROR — et pourquoi ce n'est pas une dégradation

Les 68 violations viennent **toutes de tasks déjà mergées** entrées dans la
fenêtre de new code : `report.py` (22), `journey-model.js` (14), `journey.js`
(7) — le harnais de banc des tasks 263/264 — plus quelques fichiers backend
antérieurs. C'est le phénomène déjà connu et documenté : *la new-code period
inclut des tasks déjà mergées*, donc la QG peut être rouge sans dette
introduite. La hausse 59 → 68 correspond à l'analyse de ces fichiers, pas à
cette task.

DOD « Quality Gate non dégradée sur le new code » : **tenu au sens strict** —
contribution nulle de task-265, couverture en hausse.

### Suites en Release (configuration du scan)

domain **136/136**, api **665/665**, integration **402/418** (16 skipped,
**0 échec**), application 2159/2160 et infrastructure 463/464 = les deux flaky
pré-existants connus (`MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection`,
`MailReadObjectCountTests.GetMailsByUidsOnAnEmptyPagePublishesAMeasuredZeroAsync`).

## Lint Angular log (2026-08-20)

Skip propre — `client-angular` n'est pas dans `**Repos**` (task `api-mail`
seule, `**Single frontend**: true`) et aucun fichier Angular n'a été touché.
Aucune commande lancée dans `Client/Angular/front/`, aucune opération git
(mode code-only).

## Lint mobile log (2026-08-20)

Skip propre — `client-mobile` n'est pas dans `**Repos**` et aucun fichier de
`Client/Mobile/` n'a été touché. Aucune commande, aucun commit, aucun push.

## Visual verify log (2026-08-20)

Skip propre — aucun écran `client-mobile` touché (task backend `api-mail`
seule, aucun `## Stitch design log`). Aucun serveur lancé, aucune capture.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/195 — label `awaiting-human-merge`
- `dtos-mss` : aucune modification, pas de PR (branche `fix/task-265-contenu-hors-gabarit` créée à vide par `/start`, auto-inclusion)
- Staging : task isolée hors run `/forge` — pas de branche staging pour ce cycle.

## Code Review Summary

**APPROVED** — 0 blocage.

Contenu non maîtrisé sorti du gabarit sur les **4** sites, derrière un point de
passage unique (`UntrustedPrompt.Invoke`). Le réglage `AllowDangerouslySetContent`
est **justifié par mesure** (l'encodage HTML par défaut dénaturait les bornes de
référence cliniques) et son unique contre-indication — un gabarit de chat — est
verrouillée **à l'exécution** (refus dans `Invoke`) **et** par un test. Le
best-effort du tagging est conservé mais instrumenté ; ni le compteur ni le log
ne portent de donnée de santé, et l'exception qui citerait un fragment de corps
n'est pas journalisée. Aucun `catch` élargi, aucune 500 ad hoc : la gestion
d'erreur reste au `GlobalExceptionHandler` (règle 12).

Chaque garde-fou a été **mutation-vérifié** ; la mutation du chemin résumé
reproduit l'exception de production au mot près.

Suggestions non bloquantes : `UntrustedPrompt.Invoke` reconstruit la
`KernelFunction` à chaque appel (négligeable devant l'aller-retour LLM) ; le log
du tagging passe de `Error` à `Warning`, cohérent avec le best-effort assumé et
la sentinelle d'erreurs journalisées (task-235), le compteur prenant le rôle de
signal d'alerte.
