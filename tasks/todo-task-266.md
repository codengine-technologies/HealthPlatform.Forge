# todo-task-266.md — Le serveur calcule les fils de discussion pour tout le monde, alors que deux clients sur trois les jettent

**Repos**: api-mail, client-angular, client-mobile
**Epic**: E011
**Single frontend**: false
**Dependencies**: **task-194** (`todo`) borne le **coût** du calcul. Celle-ci
supprime le calcul **quand personne ne le demande**. Les deux sont
indépendantes et composables — ni l'une ni l'autre n'attend la seconde. Si
task-194 est livrée d'abord, le gain de celle-ci reste entier : ne pas faire
un travail borné coûte toujours moins que le faire.
**Priorité**: **3** — aucun défaut fonctionnel, aucun risque patient. C'est du
travail serveur gaspillé, sur le geste le plus fréquent de la messagerie.

> **Origine** : constat fait le 2026-08-20 en instruisant task-194, sur question
> humaine (« la détection des conversations est-elle conditionnée par les
> settings de l'utilisateur côté backend ? »). Rattaché à **E011 (performance
> api-mail)** : le comportement affiché ne change pour personne.

## Objective

Que le serveur ne calcule les compteurs de fils de discussion **que lorsqu'un
client les affiche réellement**.

## Ce qui est établi — état du code au 2026-08-20

### Le réglage existe, et le backend ne le lit jamais

`UserSettingsDto` porte `MailViewMode` (`List` | `Conversation`, **défaut
`List`**), persisté par utilisateur dans `UserSetting.SettingsJson`. Une
recherche de `MailViewMode` sur `Api/Mail/src/**/*.cs` renvoie **zéro
occurrence** : le backend le stocke et le restitue, sans jamais le consulter.
(Les nombreux « Conversation » du backend appartiennent tous au **chat IA** —
`AiConversationService`, `AiChatController` — sans rapport avec le fil des
mails.)

### L'enrichissement s'exécute inconditionnellement

`OnlineMailDataProvider.GetEmailHeadersAsync` appelle
`EnrichWithThreadCountsAsync(result)` sans aucune garde (`:87`) ; la seule
condition est `if (mails.Count == 0) return;` (`:94`). Suivent **deux**
allers-retours base par page — `GetThreadCountsAsync` puis
`GetLatestMessageIdsPerThreadAsync` — dont le premier
(`MailRepository.cs:4039`) matérialise **tous** les `MessageId` de la base puis
**toutes** les lignes porteuses de `References`/`InReplyTo`, filtrées seulement
sur `FolderPath != "Sent"`.

### Deux clients sur trois jettent le résultat — vérifié sur pièce

| Client | Gate | Comportement en mode `List` |
|---|---|---|
| `client-angular` | `threadCountFor()` (`mail-list.component.ts:752-757`) et `displayedMails` (`mail-state.service.ts:262-268`) | `threadCount` → `undefined`, aucun filtrage sur `isThreadRoot`. **Les deux champs sont ignorés.** |
| `client-mobile` | `threadCountFor()` (`mail-list.component.ts:92-93`) | `isConversation ? mail.threadCount : undefined`. **Ignoré de même.** |
| `client-blazor` | **aucun** | `MailListComponent.razor` consomme `mail.ThreadCount` **toujours** (`CalculateThreadCounts`, `GetThreadCount`). Zéro occurrence de `MailViewMode` dans tout `Client/Blazor`. |

Autrement dit : pour un praticien Angular ou Mobile resté sur le **défaut**
`List`, **100 %** de ce travail serveur est jeté par le client.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer qu'on peut brancher le calcul sur `MailViewMode` côté
  serveur.** C'était l'hypothèse de départ, et elle est fausse en l'état :
  `client-blazor` n'a **aucune** notion de mode de vue et affiche ses badges de
  fil en permanence. Un court-circuit piloté par le réglage lui ferait perdre
  ses badges pour tout utilisateur en mode `List` — c'est-à-dire, par défaut,
  **tous**. Ce serait une régression fonctionnelle déguisée en optimisation.
- **Ne pas présumer que le mécanisme peut être implicite.** Une préférence
  d'**affichage** d'un client ne doit pas piloter un **calcul** serveur partagé
  par trois clients : le jour où un quatrième arrive, il hérite d'un
  comportement qu'il n'a pas demandé et qu'il ne peut pas voir.
- **Ne pas présumer que le défaut peut être « ne pas calculer ».** Tout appelant
  existant qui ne dit rien doit continuer à recevoir exactement ce qu'il reçoit
  aujourd'hui. Le défaut est **compatible**, l'économie est **opt-in**.
- **Ne pas présumer que c'est un doublon de task-194.** task-194 rend le calcul
  **moins cher** ; celle-ci le rend **absent** quand il est inutile. Aucune ne
  dispense de l'autre : un calcul borné reste un calcul, et un client qui jette
  le résultat le jette aussi vite qu'il soit optimisé.
- **Ne pas présumer que le gain se déduit.** Il se mesure, sur le banc des
  tasks 173/174, avant/après, à protocole identique.

## Décisions prises (arbitrage humain du 2026-08-20)

1. **Mécanisme = paramètre de requête explicite**, pas lecture du réglage
   serveur. Le client déclare son besoin page par page. Défaut **compatible**
   (comportement actuel) pour tout appelant muet.
2. **Périmètre = `api-mail` + `client-angular` + `client-mobile`.**
   `client-blazor` est **hors périmètre et strictement inchangé** : il ne passe
   pas le paramètre, donc il continue de recevoir les compteurs. Lui câbler un
   mode de vue est une **fonctionnalité d'affichage** à part entière, pas un
   branchement — ce sera sa propre US si le besoin est confirmé.

Les deux clients gatés doivent **réellement** envoyer le paramètre : sans cela
le mécanisme existerait sans que personne ne l'emprunte, et le gain resterait
théorique. C'est la raison d'être du périmètre à trois repos.

## Ce que la US doit livrer

1. **Un paramètre de requête** sur les endpoints de listage qui traversent
   `GetEmailHeadersAsync`, permettant à l'appelant de déclarer qu'il n'a pas
   besoin des compteurs de fils. Nom et forme laissés à l'implémentation ;
   **contrainte ferme** : absent ⇒ comportement d'aujourd'hui, à l'identique.
2. **Le court-circuit** : quand l'appelant déclare ne pas en avoir besoin,
   **aucune** des deux requêtes de fil n'est émise. Pas « une requête plus
   petite » — **zéro requête**.
3. **Angular envoie le paramètre** depuis son `mailViewMode()` déjà existant.
4. **Mobile envoie le paramètre** depuis son `isConversation` déjà existant.
5. **Mesure avant/après** sur le banc des tasks 173/174, à protocole identique,
   en mode `List` **et** en mode `Conversation` — le second doit être **inchangé**.
6. **Aucun changement d'affichage nulle part.** En mode `Conversation`, les
   compteurs et le repliement sont identiques. En mode `List`, l'écran est déjà
   identique aujourd'hui puisque les champs y sont ignorés — c'est précisément
   ce qui rend cette US sûre, et il faut le **prouver**, pas l'affirmer.

### Hors scope, explicitement

- **Le coût du calcul lui-même** → task-194. Ne pas optimiser les requêtes de
  fil ici : ce serait faire deux fois le même travail, mal.
- **Câbler un mode de vue dans `client-blazor`** → US séparée si le besoin est
  confirmé. Blazor reste inchangé.
- **Le réglage `MailViewMode` côté serveur** : il reste stocké et restitué tel
  quel, non consulté. Cette US ne lui donne pas de rôle nouveau.
- L'identité des mails → task-179.

## Definition of Done

- [ ] Build passe sur les 3 repos (0 erreur)
- [ ] Tests passent (0 échec, hors flaky pré-existants documentés)
- [ ] Test backend : appel **sans** le paramètre → les deux requêtes de fil sont
      émises et la réponse porte `ThreadCount` / `IsThreadRoot` **identiques** à
      aujourd'hui (non-régression du défaut compatible)
- [ ] Test backend : appel **déclarant ne pas en avoir besoin** → **aucune**
      requête de fil émise, vérifié par assertion sur le repository (compteur
      d'appels ou substitut strict), **pas** seulement sur la réponse
- [ ] Ce second test **doit échouer sur le code actuel** — le vérifier
      explicitement et le consigner
- [ ] Test Angular : en mode `List` le paramètre est envoyé ; en mode
      `Conversation` il ne l'est pas (ou l'inverse selon la forme retenue) —
      assertion sur l'URL appelée
- [ ] Test Mobile : idem, assertion sur l'URL appelée
- [ ] Test de non-régression d'affichage : en mode `Conversation`, compteurs
      affichés et repliement **identiques** avant/après, sur un jeu de données
      avec `In-Reply-To` et `References` variés
- [ ] **`client-blazor` non modifié** — vérifiable : `git diff` vide sur
      `Client/Blazor`
- [ ] **Mesures chiffrées avant/après** consignées dans la task, obtenues sur le
      banc (tasks 173/174) : latence p50/p95 du listage de dossier en mode
      `List` **et** en mode `Conversation`, plus le nombre de requêtes base par
      page dans chaque mode
- [ ] Le mode `Conversation` ne montre **aucune** dégradation mesurable
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Démarrer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Démarrer le front legacy : `cd Client/Angular/front && npm start`
3. Se connecter avec une boîte de test MSSanté de formation contenant **des
   fils de discussion** (au moins un fil de 3 messages ou plus).
4. **Mode `List` (défaut)** — ouvrir Paramètres, vérifier que le mode
   d'affichage est bien « Liste ». Ouvrir la boîte de réception.
   **Attendu** : la liste s'affiche exactement comme avant — un message par
   ligne, aucun badge « N messages ». Dans les journaux serveur (Seq), filtrer
   sur le listage : **aucune** requête de comptage de fil ne doit apparaître.
5. **Mode `Conversation`** — basculer le réglage, revenir à la boîte de
   réception. **Attendu** : les fils sont repliés, le badge « N messages »
   s'affiche avec **les mêmes valeurs qu'avant le correctif** (les noter à
   l'étape 4 d'une exécution de référence, ou comparer à une capture).
   Déplier un fil : mêmes messages, même ordre.
6. **Blazor inchangé** — ouvrir le client Blazor sur la même boîte.
   **Attendu** : les badges de fil s'affichent comme avant, quel que soit le
   réglage de mode de vue. C'est le point de non-régression du repo hors
   périmètre.
7. **Mobile** — répéter les étapes 4 et 5 sur `client-mobile`.
8. **Ordre de grandeur** — sur une boîte volumineuse, comparer subjectivement le
   temps d'affichage de la liste en mode `List` avant/après. La mesure opposable
   est celle du banc (DOD), pas celle-ci.

**Données de test** : boîte de formation MSSanté, aucun patient réel, aucun INS.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors exigence DSR spécifique — sujet de performance ;
  contribue indirectement à l'utilisabilité du volet MSSanté
- **Exigences DSR honorées** : non applicable — aucune exigence fonctionnelle
  nouvelle, aucun changement d'affichage
- **INS** : non applicable — aucune donnée d'identité manipulée ; le comptage de
  fils repose sur les en-têtes RFC 5322 (`Message-ID`, `In-Reply-To`,
  `References`), jamais sur l'identité du patient
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel — inchangée,
  hors périmètre
- **Habilitations** : inchangées. **Point de vigilance** : le paramètre ne doit
  **jamais** élargir le périmètre de données lues — il ne peut que **retirer**
  du calcul, jamais en ajouter. Un paramètre qui ferait lire plus serait un
  défaut de conception, pas une option
- **Interop CI-SIS** : non applicable — aucun format d'échange métier touché
- **Tracé PGSSI-S** : inchangé. Ne pas supprimer de journalisation existante en
  supprimant le calcul ; l'absence de calcul peut être tracée en `Debug`, sans
  objet de message ni contenu
- **Consentement patient** : non applicable — aucun partage, aucune alimentation
  DMP / Mon Espace Santé
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — cible inchangée
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau. Le correctif
  **réduit** le volume de données lues côté serveur (moins de lignes
  matérialisées), il n'en élargit aucun périmètre
