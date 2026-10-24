# todo-task-394.md — Une rédaction sans texte dans le corps ne laisse ni brouillon ni question (weda2 et mobile)

**Repos**: api-mail, client-angular, client-mobile
**Dependencies**: aucune
**Epic**: E009
**Single frontend**: false
**Priorité**: **3** — défaut visible du médecin : fermer un message vide pose une question inutile (weda2), et des
brouillons sans contenu s'accumulent dans « Brouillons ».

> **Origine.** Signalement de l'humain, 2026-10-24 : « lorsque je compose un nouvel email, et que je ne saisis rien
> dans le corps du message, que je quitte par la croix, je ne devrais pas avoir de message de confirmation concernant
> le brouillon puisque rien n'a été saisi. Idem, assure-toi qu'un brouillon ne s'enregistre pas si dans le corps rien
> n'a été saisi. »

## Ce qui est établi

- **weda2** (`libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`) :
  - la croix appelle **toujours** `requestDiscard()`, qui affiche « abandonner le brouillon ? », même pour une
    rédaction vide ;
  - l'enregistrement (automatique toutes les 30 s, en quittant, avant d'ouvrir une autre rédaction) passe par
    `hasUnsavedContent()` → `hasContent()`. Un objet, un destinataire ou une pièce jointe y suffisent ; pour le corps,
    `hasOwnText` exclut déjà la signature.
- **mobile** (`src/app/features/mail/components/mail-compose/mail-compose.component.ts`) :
  - la croix enregistre le brouillon sans rien demander, si `hasDraftContent()` ;
  - `hasDraftContent()` compte l'objet, les destinataires et **tout** le texte du corps (`htmlToText`), signature
    comprise. `splitOwnText` (`core/utils/spelling-correction.util.ts`) sait déjà isoler le texte du médecin.

## Décisions actées (humain, 2026-10-24)

1. **Un brouillon n'existe que si le médecin a écrit dans le corps du message.** Le « texte du médecin » est le corps
   **sans la signature et sans la citation** du message d'origine (réponse, transfert). Un objet, un destinataire ou
   une pièce jointe, sans texte, ne suffisent pas : la rédaction se ferme sans brouillon, et ils sont abandonnés.
2. **Périmètre : weda2 et mobile**, même règle.

## Objective

Fermer une rédaction où le médecin n'a rien écrit dans le corps ne pose aucune question et ne crée aucun brouillon. Une
rédaction où il a écrit se comporte comme aujourd'hui.

### Règles

- **Sans texte du médecin dans le corps** :
  - **weda2** : la croix ferme la rédaction tout de suite, sans « abandonner le brouillon ? » ;
  - **mobile** : la croix et le geste de fermeture ferment sans enregistrer ;
  - **les deux** : l'enregistrement automatique (30 s), l'enregistrement en quittant la rédaction (autre message, autre
    dossier) et celui qui précède l'ouverture d'une autre rédaction n'enregistrent rien ;
  - l'alerte du navigateur à la fermeture de l'onglet (weda2, `beforeunload`) ne se déclenche pas.
- **Avec du texte du médecin** : comportement inchangé (weda2 : confirmation à la croix ; mobile : enregistrement à la
  croix ; enregistrement automatique et en quittant).
- **Réponse et transfert** : la citation du message d'origine n'est pas du texte du médecin. Ouvrir « Répondre » puis
  fermer sans écrire ne laisse rien.
- **Brouillon déjà enregistré, rouvert depuis « Brouillons »** (décision PO, cohérente avec la règle 1) : s'il porte du
  texte du médecin, rien ne change. Si le médecin efface tout son texte puis ferme, le brouillon existant n'est **ni
  supprimé ni écrasé en silence** : weda2 garde la confirmation d'abandon (qui supprime le brouillon) ; le mobile ne
  l'enregistre pas vide et le laisse tel qu'il était.
- **La signature seule n'est pas du texte** (déjà le cas sur weda2, nouveau sur le mobile).

### Hors périmètre

- Côté API, l'enregistrement d'un brouillon vide reste accepté : la règle est une règle de saisie, portée par les
  clients. Blazor.

## Gherkin

Voir `tests/Features/Mss/EmptyComposeLeavesNoDraft.feature`.

## Parcours e2e

| Scénario | Version | Comportement | mobile | angular |
|---|---|---|---|---|
| `E2E-DRAFT-004` (nouveau) | 1 | « Nouveau message », destinataire et objet saisis, corps vide, fermeture par la croix : aucune question (weda2), et aucun brouillon côté serveur (relu par l'API, liste des brouillons inchangée). Seed `boite-praticien`. | requis | requis |
| `E2E-DRAFT-001`, `E2E-DRAFT-002` | inchangée | Comportement attendu identique. Les aides mobiles saisissent désormais du texte dans le corps (elles créaient un brouillon avec un objet seul). | requis | requis |
| `E2E-DRAFT-003` | inchangée | Le parcours écrit déjà un texte : inchangé. | requis | requis |

## Definition of Done

- [ ] Build et tests verts : client-angular (weda2, `mss-lib`), client-mobile ; api-mail (`ScenarioCatalogTests`)
- [ ] Scénario E2E-DRAFT-004 ajouté (version 1) dans `Api/Mail/e2e/scenarios.yml`, et implémenté dans le mobile et dans
      weda2, prouvé rouge par mutation sur chaque client
- [ ] E2E-DRAFT-001, 002 et 003 verts sur les deux clients, sans montée de version
- [ ] weda2 — tests de composant, rouges d'abord : croix sans texte → aucune confirmation, rédaction fermée, aucun appel
      d'enregistrement ; objet + destinataire + pièce jointe sans texte → idem ; signature seule → idem ; réponse ou
      transfert sans texte → idem ; avec texte → confirmation inchangée ; enregistrement automatique, en quittant et
      avant une autre rédaction : aucun appel sans texte ; brouillon rouvert vidé de son texte → confirmation d'abandon
      gardée ; `beforeunload` sans texte → pas d'alerte
- [ ] mobile — tests de composant, rouges d'abord : croix et geste sans texte → aucun enregistrement ; objet et
      destinataire sans texte → idem ; signature seule → idem ; réponse ou transfert sans texte → idem ; avec texte →
      enregistrement inchangé ; enregistrement automatique sans texte → aucun appel ; brouillon rouvert vidé de son texte
      → aucun enregistrement vide
- [ ] Trou du filet : ligne ajoutée dans « Trous du filet » de `conventions/e2e.md` (défaut vu par l'humain, non vu par
      `/e2e`), E2E-DRAFT-004 prouvé rouge sur le comportement d'avant
- [ ] `data-testid` existants conservés ; aucune chaîne en dur hors libellés du client

## Manual Test Plan

- weda2 : banc e2e (`Client/Angular/front`, weda2 en `--serve-only`) ou weda2 local ; mobile : `cd Client/Mobile && npm
  start`.

1. « Nouveau message », ne rien saisir, fermer par la croix : weda2 ne pose aucune question ; rien dans « Brouillons »
   (les deux clients).
2. « Nouveau message », saisir un destinataire et un objet, corps vide, fermer : aucune question (weda2), rien dans
   « Brouillons ».
3. Même chose en attendant plus de 30 s avant de fermer : rien dans « Brouillons ».
4. Ouvrir un message, « Répondre », ne rien écrire, fermer : aucune question, aucun brouillon.
5. « Nouveau message », écrire une phrase dans le corps, fermer : weda2 demande « abandonner le brouillon ? » comme
   avant ; le mobile enregistre le brouillon, qui apparaît dans « Brouillons ».
6. Rouvrir ce brouillon, effacer tout le texte, fermer : weda2 demande la confirmation d'abandon ; le mobile ferme sans
   écraser le brouillon, qui garde son texte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Correctif d'ergonomie de la rédaction, aucun échange modifié.
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable. Aucune donnée d'identité n'est manipulée.
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : aucun nouvel évènement ; moins de brouillons vides stockés
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui, stockage des brouillons inchangé
- **AIPD / impact RGPD** : inchangé. La règle réduit les données conservées (brouillons sans contenu).
