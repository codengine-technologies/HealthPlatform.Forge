# todo-task-089.md — Blocage du contenu distant des courriers (anti-pistage)

**Repos**: api-mail, client-blazor, client-angular
**Epic**: E009

## Objective

Empêcher le **chargement automatique des ressources distantes** (images, pixels
traceurs, ressources externes) contenues dans le corps HTML des courriers.
Inspiré du mécanisme `show_images` / « charger les images » de Roundcube. Sur
une messagerie de santé, le chargement silencieux d'un pixel distant confirme à
un tiers la lecture d'un courrier (fuite d'information et confidentialité
patient) et expose l'IP/poste du professionnel.

## Comportement attendu

- Par défaut, les ressources distantes (`<img src="http…">`, arrière-plans CSS
  distants, ressources externes) ne sont **pas chargées** à l'ouverture d'un
  courrier ; les sources distantes sont neutralisées (réécriture / suppression).
- Une **bannière non bloquante** informe le PS que des images distantes ont été
  bloquées, avec une action « Afficher les images ».
- Le clic sur « Afficher les images » charge les ressources distantes **pour ce
  courrier uniquement** (pas de mémorisation par défaut).
- Les images **embarquées** (pièces jointes inline `cid:`) restent affichées
  normalement — seules les ressources **distantes** sont bloquées.
- Le comportement est cohérent entre Blazor et Angular.

## Gherkin

```gherkin
Feature: Blocage du contenu distant des courriers

  Scenario: Images distantes bloquées par défaut
    Given un courrier contenant une image hébergée sur un serveur externe
    When le médecin ouvre ce courrier
    Then l'image distante n'est pas chargée
    And une bannière propose d'afficher les images

  Scenario: Affichage à la demande
    Given un courrier dont les images distantes ont été bloquées
    When le médecin choisit d'afficher les images
    Then les images distantes de ce courrier sont chargées

  Scenario: Les images embarquées restent affichées
    Given un courrier contenant une image embarquée en pièce jointe
    When le médecin ouvre ce courrier
    Then l'image embarquée est affichée sans blocage
```

## Definition of Done

- [ ] Build passes sur chaque repo listé (0 erreur)
- [ ] Neutralisation des ressources distantes dans le HTML de courrier (réécriture des `src`/url() distants) — cohérente avec l'assainissement de la task-088
- [ ] Distinction ressource distante (bloquée) vs ressource embarquée `cid:` (affichée)
- [ ] Blazor : bannière « images bloquées » + action « Afficher les images » (ce courrier), aucune chaîne en dur (i18n), `data-testid`
- [ ] Angular : idem côté front legacy, aucune chaîne en dur (i18n), `data-testid`
- [ ] L'affichage à la demande ne mémorise pas l'expéditeur par défaut
- [ ] >= 1 test unitaire par comportement (distant bloqué, embarqué préservé, affichage à la demande)
- [ ] >= 1 test de composant par frontend (bannière affichée, action recharge les images)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer Blazor : `cd Client/Blazor && dotnet run`
- Lancer Angular : `cd Client/Angular && npm start`
- Ouvrir un courrier contenant une image distante (`<img src="https://…">`)
  → vérifier qu'elle n'est pas chargée et que la bannière apparaît
- Cliquer « Afficher les images » → vérifier le chargement pour ce courrier
- Ouvrir un courrier avec image inline (`cid:`) → vérifier l'affichage direct
- Surveiller les requêtes réseau : aucune requête vers le serveur distant avant
  l'action explicite du PS

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : exigence transverse de sécurité / confidentialité (PGSSI-S)
- **Exigences DSR honorées** : PGSSI-S § confidentialité — non-divulgation de la lecture d'un courrier de santé
- **INS** : non applicable
- **Authentification PS** : inchangé
- **Habilitations** : inchangé
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : optionnel — journaliser l'action « afficher les images » (sans contenu)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Sécurité / confidentialité** : empêcher la fuite d'accusé de lecture implicite (pixel traceur) et l'exposition de l'IP/poste du PS à un tiers
- **Hébergement HDS** : oui — environnement existant
- **AIPD / impact RGPD** : amélioration de la confidentialité — mesure à mentionner dans l'AIPD
