# todo-task-277.md — Une session coupée par le serveur ne remonte plus une erreur au médecin

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

Le médecin voit une **erreur technique** quand la session réutilisée par
api-mail a été fermée par le serveur d'en face. Le message qu'il reçoit ne
décrit rien qu'il puisse comprendre ni corriger : « Une erreur inattendue s'est
produite. Veuillez réessayer plus tard. »

Le tir du 2026-08-29
(`Api/Mail/tests/loadtest-k6/reports/2026-08-29/report-journey-500-task270-20260829-220155.md`,
finding **F-POOL-1**) en donne **deux occurrences, sur les deux protocoles**, à
500 médecins :

| Quand | Route | Pile | Fenêtre |
|---|---|---|---|
| 20:29 | `POST /api/v1/mail/sendmail` | `SmtpCommandException: Service shutting down and closing transmission channel (socket timeout, SO_TIMEOUT: 30000ms)` → `OnSenderNotAccepted` → `MailFromAsync`, `SmtpService.cs:95` | chauffe |
| 21:34 | `GET /api/v1/mail/folders/INBOX` | `IOException` / `SocketException (10054)` → `ImapFolder.StatusAsync` → `ImapService.ReadFolderAsync`, `ImapService.cs:658`, `ElapsedMs=19217` | **régime** |

Le volume dit que la situation n'est pas exceptionnelle, elle est **absorbée
partout ailleurs** : **4 727 `SmtpCommandException`** pour **142 467** NOOP de
keep-alive sur la fenêtre (3,3 % des NOOP échouent), **1 092 `IOException`** et
**619 `SocketException`**. Sur tout ce volume, **deux** seulement ont atteint le
médecin — mais deux de trop, et le taux croît avec la population et avec la
fragilité du lien.

**Ce n'est pas une régression de task-270.** Le helper de mapping d'erreur
`MapFolderAccessExceptionAsync` **préexiste** à `99f855d` (3 sites d'appel
avant, 2 après — l'écart vient de la fusion des deux chemins, pas d'une reprise
supprimée). Le défaut est ancien et structurel : **une session poolée que le
serveur a fermée de son côté est utilisée telle quelle**, l'échec remonte au
`GlobalExceptionHandler` et sort en `ProblemDetails` 500 (règle 12 — le format
est correct, c'est la décision de rendre une erreur qui ne l'est pas).

**Intention métier** : une connexion morte est un incident d'infrastructure, pas
un résultat métier. Elle doit être **détectée et re-tentée une fois sur une
session fraîche** avant que quoi que ce soit remonte au praticien. Le médecin ne
voit une erreur que si la seconde tentative échoue aussi.

### ⚠️ Le point dur, à trancher DANS l'US : l'idempotence du rejeu SMTP

Re-tenter une lecture IMAP est sans conséquence. **Re-tenter un envoi ne l'est
pas** : le point de non-retour est le `DATA` accepté par le serveur MSSanté.

| Étape SMTP | Rejeu | Pourquoi |
|---|---|---|
| Échec avant/pendant `MAIL FROM` (cas mesuré) | **sûr** | le serveur n'a rien accepté |
| Échec pendant `RCPT TO` | **sûr** | idem |
| Échec après `DATA` accepté | **INTERDIT** | le message peut être parti — rejouer, c'est envoyer deux fois un courrier médical |
| Échec sur l'acquittement final | **INTERDIT sans preuve** | indécidable en l'état |

L'US doit **nommer explicitement** le point de non-retour dans le code, et le
fixer par un test. Un doublon d'envoi MSSanté est un incident métier bien plus
grave que l'erreur qu'on cherche à éviter.

### Contenu attendu

1. **Détecter la session morte** — sur les deux voies, distinguer « le serveur a
   fermé la connexion » (`SocketException 10054`, `IOException`,
   `ServiceNotConnectedException`, `SmtpCommandException` de type « shutting
   down ») d'une erreur métier légitime. **Mapping par type, jamais par
   heuristique de message** (règle 12).
2. **Re-tenter une fois** sur une session fraîche, en écartant la session morte
   du pool.
3. **Borner le rejeu SMTP** au point de non-retour ci-dessus.
4. **Rendre la reprise observable** — un compteur de reprises par voie, pour que
   le prochain tir puisse dire combien de 500 ont été évités, et pour que la
   disparition du signal ne soit pas confondue avec l'absence d'instrument
   (leçon task-214).

**Gain attendu** : aucun temps serveur — de la **robustesse**. La grandeur à
suivre est le nombre d'erreurs vues du médecin, pas une latence.

**Ce qui n'est PAS dans le périmètre** : les 4 727 `SmtpCommandException`
elles-mêmes — elles viennent du GreenMail du banc qui coupe sur son `SO_TIMEOUT`
de 30 s, c'est un plafond **du serveur de test**, pas un défaut d'api-mail. On
corrige ce que l'application en fait, pas leur nombre.

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec)
- [ ] Une session IMAP fermée par le serveur déclenche **une** reprise sur
      session fraîche — test unitaire par simulation de `SocketException 10054`
      sur `StatusAsync`
- [ ] Une session SMTP fermée avant `DATA` déclenche **une** reprise — test
      unitaire
- [ ] Un échec **après** `DATA` accepté ne déclenche **aucune** reprise — test
      unitaire dédié, c'est la garde anti-doublon
- [ ] La détection se fait **par type d'exception**, jamais par mot-clé sur le
      message (règle 12) — test qui échoue si une heuristique de chaîne réapparaît
- [ ] La seconde tentative en échec rend un `ProblemDetails` conforme (règle 12),
      sans stack trace ni donnée de santé dans le `detail`
- [ ] Compteur de reprises par voie (`imap` / `smtp`) publié et testé
- [ ] La session morte est retirée du pool et n'est pas resservie — test
- [ ] Aucune donnée de santé dans les journaux de reprise : ni destinataire, ni
      objet, ni contenu du message, ni INS

## Manual Test Plan

**Ce que l'humain valide au HAG** : qu'une coupure de connexion ne se voit plus,
et qu'un envoi n'est jamais dupliqué.

1. Lancer le banc :
   ```bash
   cd Api/Mail
   dotnet run --project src/AppHost --launch-profile https-load-test
   ```
2. Attendre `http://127.0.0.1:5052/api/v1/connection/status` en 200, puis
   seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 2 --messages 20 --api http://127.0.0.1:5052`
3. Ouvrir `INBOX` une première fois pour établir la session poolée (en-têtes
   d'identité virtuelle, `Client-Session-Id: sess-1`).
4. **Couper la connexion sous l'application** via l'API Toxiproxy — ajouter un
   toxic de reset sur `dovecot-imap` :
   ```bash
   curl -s -X POST http://127.0.0.1:8474/proxies/dovecot-imap/toxics \
     -H 'Content-Type: application/json' \
     -d '{"name":"kill","type":"reset_peer","stream":"downstream","attributes":{"timeout":0}}'
   ```
5. Rouvrir `INBOX`, puis retirer le toxic :
   `curl -s -X DELETE http://127.0.0.1:8474/proxies/dovecot-imap/toxics/kill`
6. **Vérifier** : le médecin obtient sa liste de messages — **pas** de 500. Le
   compteur de reprises IMAP a augmenté de 1 (journaux ou `/metrics`).
7. **Envoi — le point sensible.** Répéter l'opération 4 sur `greenmail-smtp`,
   puis envoyer un message via `POST /api/v1/mail/sendmail`. Retirer le toxic.
8. **Vérifier** : l'envoi aboutit (ou échoue proprement), et surtout —
   **inspecter la boîte du destinataire : le message doit y être présent une
   seule fois**. Un doublon est un échec bloquant de l'US.
9. Vérifier qu'aucun journal produit à l'occasion de la reprise ne contient
   d'adresse MSSanté de destinataire, d'objet ni de contenu de message.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — robustesse technique interne
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé en nominal
- **INS** : non applicable
- **Authentification PS** : inchangée — la reprise réutilise l'identité de la requête en cours, jamais une identité de service
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — IMAP/SMTP internes au périmètre MSSanté existant
- **Tracé PGSSI-S** : **ajout** — journaliser chaque reprise de session (voie, cause typée, résultat), sans donnée de santé ; durée de conservation alignée sur les journaux techniques existants. L'échec d'envoi définitif reste journalisé comme aujourd'hui.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle collectée ; le compteur de reprises est une métrique technique sans identifiant
