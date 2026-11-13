# todo-task-479 — Serveur MCP messagerie : lire un message, tracé au nom du médecin, jamais marqué lu

**Repos**: api-mail, api-mcp
**Dependencies**: done-task-478
**Epic**: E026
**Single frontend**: true

> **Origine.** Suite de task-478, décidée avec l'humain le 2026-11-13. L'assistant IA doit pouvoir lire le
> contenu d'un message. Deux contraintes :
> - **une lecture par le MCP ne marque jamais le message comme lu** (décision humaine du 2026-11-13) ;
> - la règle 14 exige que la lecture soit tracée au nom de son auteur réel.
>
> Or api-mail ne trace pas la lecture d'un contenu : `GET …/emails/content/{id}` est `TraceExempt`
> (`Api/Mail/src/Api/Controllers/V1/MailController.cs:693`), et la trace `MailRead` n'est écrite qu'au passage à
> « lu ». Sans cette task, une lecture par l'assistant ne laisserait aucune trace.
>
> **Ne démarre qu'une fois task-466 terminée** (api-mail doit être revenu sur `develop`).

## Objectif

Le médecin demande à l'assistant de lire un message ou de résumer un compte rendu. Le serveur MCP rend le
contenu du message. api-mail trace cette consultation au nom du médecin, avec le canal « assistant IA ». Le
message reste **non lu** dans toutes les applications.

## Règles métier

1. **Jamais marqué lu.** La lecture par le MCP ne change ni le drapeau « lu » IMAP, ni l'état local, ni les
   compteurs de non lus, ni les files « à acquitter » (biologie). Elle n'envoie aucun accusé de lecture.
2. **Toujours tracée.** Chaque contenu rendu au MCP écrit une trace « message consulté via l'assistant IA »
   portant le RPPS et le nom PSC de la personne, son rôle, la boîte, l'instant et le message. Cette trace est
   visible dans le journal de la boîte comme les autres (règle 14) et suit la famille `HealthDataAccess`
   (3 653 jours).
3. **Le canal n'est pas déclaratif.** api-mail reconnaît le canal MCP à un élément que les autres clients ne
   peuvent pas présenter (par exemple le client Keycloak / `azp` du jeton, ou une route dédiée réservée à ce
   client), pas à un en-tête libre. Le choix du mécanisme revient à `/develop`. Un client ordinaire qui lit un
   contenu garde le comportement actuel.
4. **Pièces jointes** : hors scope. L'outil rend le corps texte et la **liste** des pièces jointes (nom, type,
   taille), pas leur contenu.

## Comportement attendu

- Nouvel outil MCP `read_message(mailbox, folder, messageId)` → corps texte du message (HTML converti en texte),
  en-têtes, liste des pièces jointes.
- Côté api-mail : la lecture faite pour le MCP écrit la trace « consulté via l'assistant IA » et ne touche à
  aucun état de lecture.

## Definition of Done

- [ ] Build + tests verts sur api-mail et api-mcp
- [ ] Test d'intégration api-mail de bout en bout (vraie pile, vrai PostgreSQL, IMAP du fixture) : la lecture d'un contenu par le canal MCP rend le corps **et** écrit la trace « consulté via l'assistant IA » avec l'auteur réel (RPPS, rôle) et la boîte, lue dans le journal d'audit ; le message reste **non lu** côté IMAP (pas de `\Seen`) et en base. Cas d'échec : sans le canal MCP, aucune trace « assistant » n'est écrite. Vu rouge (règle 1b)
- [ ] Test d'intégration api-mail : **deux personnes sur la même boîte** (titulaire et délégataire) lisent le même message par le MCP ; chaque trace porte son auteur réel (règle 14)
- [ ] Test d'intégration api-mail : un client qui présente seulement un en-tête imitant le canal MCP n'obtient pas la trace « assistant » (le canal n'est pas déclaratif) ; vu rouge
- [ ] Test d'intégration api-mcp : `tools/call read_message` lu dans la réponse réelle (corps + liste des pièces jointes) ; la requête reçue par api-mail simulé est celle du canal MCP ; la liste blanche des routes de task-478 est étendue à cette seule route ; vu rouge
- [ ] Aucune route d'état de lecture appelée (liste blanche de task-478, mutation prouvée rouge)
- [ ] Aucun contenu de message dans les journaux d'api-mail ni d'api-mcp

## Manual Test Plan

Même pile que task-478.
1. Dans Claude Code connecté au serveur « messagerie » : « Lis-moi le dernier message non lu de la boîte de
   réception » → contenu du message.
2. Ouvrir l'application mobile ou Angular : ce message est **toujours non lu**.
3. Journal d'audit de la boîte : une ligne « consulté via l'assistant IA », au nom du médecin connecté.
4. Se connecter au MCP comme délégataire de la même boîte et lire le même message : une deuxième ligne, au nom
   du délégataire.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — canal d'accès, cf. task-478
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : non applicable — cf. task-478
- **INS** : non applicable — le contenu est relayé sans traitement d'identité patient
- **Authentification PS** : PSC e-CPS en CIBA, cf. task-478
- **Habilitations** : décidées par api-mail (règle 14), inchangées
- **Interop CI-SIS** : non applicable — les CDA joints ne sont pas rendus dans cette task
- **Tracé PGSSI-S** : nouvelle action « message consulté via l'assistant IA », auteur réel, rôle, boîte, instant, message ; famille `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable — accès du médecin à sa messagerie
- **Référentiels métier** : aucun
- **Hébergement HDS** : le **contenu** des messages sort vers l'éditeur du client IA. L'arbitrage de task-478 (DPO / RSSI, avant mise en production) s'étend ici au contenu, qui est la donnée la plus sensible
- **AIPD / impact RGPD** : à mettre à jour, cf. task-478
