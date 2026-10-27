# task-400 — GELÉE (décision humaine du 2026-10-27)

**Ne pas relancer `/e2e task-400`.** La demande « libérer les ports » ci-dessous est caduque.

## Pourquoi

Mailiz ne déploie plus l'espace de noms IMAP `shared/<adresse du délégant>/…`, sur lequel reposent
task-397, task-398, task-399 (mergées sur `develop`) et cette task. Selon l'ANS, le délégataire se
connecte **directement à la BAL du délégant** avec **son propre jeton PSC** (XOAUTH2 : identifiant =
adresse du délégant, jeton = celui du délégataire), une fois les droits donnés par le délégant.
L'humain l'a vérifié sur l'environnement de formation.

## État conservé

- Branche api-mail `feat/task-400-delegation-tracer-ce-qui-agit` : poussée, 7 commits, **aucune PR**.
- `dtos-mss` 547.0.0 : publié (contrat d'audit).
- weda2 (`Client/Angular`) : code de la task **non commité** (33 fichiers), à mettre de côté par
  l'humain (`git stash push -m "task-400 gel"`) : la forge ne touche pas au git de ce dépôt.

## Reprise

Après le retrait (ou l'adaptation) du code `shared/` et l'étude de la bascule de BAL par le registre.
L'audit « qui agit dans quelle BAL » reste pertinent dans le nouveau modèle ; sa détection d'un acte
délégué (aujourd'hui par le chemin `shared/`) sera à réécrire.

---

# (caduc) task-400 — /e2e bloqué : outillage (ports du banc occupés)

**Nature du blocage : outillage.** Ni régression, ni écart de parité constatés : les voies n'ont pas pu
démarrer.

## Constat (2026-10-27)

- Le port **5052** est tenu par `dcp.exe` (PID 70596), le contrôleur Aspire de l'AppHost lancé sur le poste.
- Le port **4200** est tenu par un `node.exe` (PID 56544), le serveur de dev weda2.
- Les deux voies e2e (mobile et Angular) publient 5052 ; la voie Angular sert aussi weda2 sur 4200.
- La forge n'arrête pas les processus de l'humain : aucune voie n'a été jouée.

## État de la task

Tout le reste de la chaîne est vert :

- `/develop` : contrat `dtos-mss` 547.0.0 publié ; api-mail poussé ; weda2 écrit (code seul, non commité) ;
- `/sonar` : QG OK, 0 défaut sur le nouveau code, new coverage 95,1 % ;
- `/lint-angular` : 0 erreur ; `/lint-mobile` : sans objet.

Le parcours **E2E-DELEG-008** (nouveau) est écrit et typé, mais n'a encore jamais tourné : sa preuve par
mutation reste à faire au premier passage de la voie Angular.

## Décision demandée

Libérer les ports 5052 et 4200 (arrêter l'AppHost et le serveur de dev weda2), puis relancer :

```
/e2e task-400
```

La chaîne reprend seule (`/review`, puis `/tech-writer`) si les voies sont vertes. Si tu préfères ne pas
rejouer les parcours pour cette task, c'est ton seul arbitrage : écrire à la main, sous `**Repos**:`,
`**E2E**: bypass — décision humaine du {date}`, puis lancer `/e2e task-400`.
