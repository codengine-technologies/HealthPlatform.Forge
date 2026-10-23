# todo-task-387.md — « Aujourd'hui » est le jour du médecin, pas celui du serveur

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: false
**Priorité**: **3** — entre minuit et 2 h (heure de Paris, été), l'encart « Aujourd'hui » du tableau de bord et le
résumé des non-lus du jour peuvent montrer la mauvaise journée ; la suite d'intégration d'api-mail échoue sur cette
plage horaire.

> **Origine.** task-386, `/review` du 2026-10-23 à 00 h 03 puis 01 h 32 (heure de Paris) : trois tests d'intégration
> « messages du jour » rouges — `EmailReadingUseCaseTests.FilterTodayEmailsShouldReturnOnlyTodayAsyncAsync`,
> `ImapFolderServiceIntegrationTests.GetFolderTodayAsync_Inbox_ShouldReturnTheMessageOfTheDayAsync`,
> `ImapFolderServiceIntegrationTests.GetFolderNotSeenTodayAsync_Inbox_ShouldReturnTheUnreadMessageOfTheDayAsync`.
> Rouges aussi sur `origin/develop` à la même heure (worktree), verts le reste de la journée.

## Ce qui est établi (lecture du code, 2026-10-23)

- `ImapFolderService` (l. ~241 et ~247) cherche « aujourd'hui » par `SearchQuery.DeliveredAfter(DateTime.Now.Date)` :
  le **jour local de la machine qui fait tourner api-mail**. Le serveur IMAP, lui, compare la date interne des
  messages dans **son** fuseau (`SEARCH SINCE` ne porte qu'une date).
- Le cache Redis de cette recherche (`RedisKeys`, champ `ScopeDay`) porte lui aussi le « jour local de calcul ».
- Conséquence en test : la machine est à J (Paris), le conteneur IMAP est encore à J-1 (UTC) → le message déposé
  « maintenant » a une date interne J-1 et sort du filtre « depuis J ».
- Conséquence possible en production : api-mail tourne en conteneur, a priori en UTC → entre 00 h et 02 h à Paris,
  « aujourd'hui » vaut encore la veille côté api-mail : l'encart affiche les messages d'hier comme ceux du jour.
  **À confirmer** (fuseau réel des conteneurs dev / prod) pendant `/develop`.

## Objective

« Aujourd'hui » désigne la journée **civile du médecin** (fuseau de référence, Europe/Paris par défaut), quels que
soient le fuseau de la machine qui fait tourner api-mail et celui du serveur de messagerie. Le calcul ne lit plus
l'horloge système directement : il passe par une horloge injectée (`TimeProvider`), ce qui rend le comportement
testable à n'importe quelle heure, minuit compris.

### Périmètre

1. Un fuseau de référence configurable (option, Europe/Paris par défaut) ; « aujourd'hui » = la date civile dans ce
   fuseau, calculée depuis `TimeProvider`.
2. La recherche IMAP du jour couvre toute la journée de référence, même si le serveur IMAP est dans un autre fuseau
   (borne `SINCE` élargie d'un jour, puis filtre exact sur la date de réception convertie dans le fuseau de
   référence — à confirmer selon ce que renvoie l'enveloppe).
3. Le cache du jour (`ScopeDay`) suit le même jour de référence.
4. Les trois tests cités deviennent déterministes (horloge injectée, aucune dépendance à l'heure du run).

**Hors périmètre** : un fuseau par médecin (lu dans le profil ou le navigateur) — voir « Point à confirmer ».

## Gherkin

```gherkin
Feature: The "today" view follows the doctor's day

  Scenario: Shortly after midnight, yesterday's messages are no longer "today"
    Given a doctor in France with a message received yesterday evening
    And a message received a few minutes after midnight
    When the doctor opens today's messages at half past midnight
    Then only the message received after midnight is shown

  Scenario: A message received late in the evening is still "today"
    Given a doctor in France
    When a message arrives at 23:50
    And the doctor opens today's messages at 23:55
    Then the message is shown

  Scenario: Today's unread summary follows the same day
    Given a doctor in France with an unread message received yesterday evening
    When the doctor opens the unread summary of the day just after midnight
    Then yesterday's message is not counted
```

## Definition of Done

- [ ] Build et tests verts : api-mail
- [ ] « Aujourd'hui » calculé dans un fuseau de référence configurable (Europe/Paris par défaut) à partir d'un
      `TimeProvider` injecté ; plus aucun `DateTime.Now` / `DateTime.Today` dans les chemins « du jour »
      (`ImapFolderService`, cache `ScopeDay`, et tout autre usage relevé par `grep` dans `src/`)
- [ ] Test d'intégration de bout en bout pour `GET /api/v1/mail/folders/{folder}/emails/today` : à 00 h 30 (horloge
      simulée, fuseau de référence Europe/Paris), un message reçu la veille à 23 h 00 n'est **pas** dans la réponse et
      un message reçu à 00 h 10 l'est ; vu rouge sur le code actuel (règle 1b)
- [ ] Test d'intégration de bout en bout pour `GET /api/v1/mail/folders/{folder}/emails/unread-today` (route exacte à
      relever) : même cas limite, lu dans la réponse réelle ; vu rouge (règle 1b)
- [ ] Test : serveur IMAP dans un autre fuseau que la référence (UTC) → un message reçu à 23 h 50 heure de Paris est
      bien « du jour »
- [ ] Cache du jour : une entrée calculée la veille (jour de référence) est ignorée après minuit de référence
- [ ] Les trois tests cités sont verts quelle que soit l'heure du run (rejoués avec une horloge simulée à 00 h 30, à
      01 h 59 et à 23 h 55, heure de Paris)
- [ ] Fuseau réel des conteneurs api-mail (dev, et prod si accessible) relevé et consigné au `## Develop log`
- [ ] Aucune donnée de santé en clair dans les logs (le jour de référence peut être journalisé, pas le contenu)

## Manual Test Plan

1. Lancer api-mail avec `TZ=UTC` (comportement conteneur) et une boîte de test.
2. Déposer un message ; vérifier qu'il apparaît dans l'encart « Aujourd'hui » du tableau de bord (weda2 et mobile).
3. Avec l'option de fuseau ou une horloge de démonstration, se placer à 00 h 30 heure de Paris : les messages de la
   veille ne figurent plus dans « Aujourd'hui ».
4. Lancer la suite d'intégration d'api-mail entre 00 h et 02 h (heure de Paris) : verte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de présentation (fenêtre de date), aucune exigence nouvelle
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne fixe la notion de « jour » de la messagerie
- **INS** : non applicable — aucune donnée patient manipulée, seul un filtre de date change
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel, déjà exigé par les routes concernées
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — recherche IMAP, aucun échange de document
- **Tracé PGSSI-S** : inchangé — aucune nouvelle action tracée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucune donnée nouvelle, aucun stockage nouveau (le cache existant reste le même)
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement

## Point à confirmer (humain)

> Fuseau de référence : **Europe/Paris pour tous** (proposition par défaut), ou un fuseau **par médecin** pour les
> praticiens des DROM (Guadeloupe, Martinique, Réunion, Guyane, Mayotte) ? Le second demande de connaître le fuseau
> de chaque utilisateur (profil ou navigateur) et sort du périmètre de cette task.
