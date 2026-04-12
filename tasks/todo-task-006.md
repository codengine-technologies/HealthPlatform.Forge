# todo-task-006.md — Annule et remplace

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: todo-task-001 (en-tetes SMTP), todo-task-002 (masquage prefixe XDM)

## Objectif

Le systeme doit permettre au professionnel de renvoyer un document medical avec une
mention pre-parametree "annule et remplace" lorsqu'il souhaite corriger ou mettre a jour
un document precedemment transmis via MSSante. Cela couvre le cas ou un professionnel a
transmis un document errone (erreur de patient, resultats incomplets, correction de
diagnostic) et doit le corriger aupres du ou des destinataires originaux.

## Contexte reglementaire

L'exigence AMBU.MSS/va1.02 impose que le systeme permette l'envoi d'une nouvelle
version d'un document avec mention "annule et remplace". Le Ref#2 ne prescrit pas de
mecanisme technique specifique (pas de lien formel entre l'ancien et le nouveau message
au niveau SMTP/IMAP). La mention est une indication fonctionnelle visible par le
destinataire.

Le message de remplacement doit neanmoins respecter les exigences du Ref#2 applicables
a tout envoi :
- **ECO.2.1.1** — un seul usager par message, archive IHE_XDM + PDF/A-1
- **ECO.2.1.3** — format de l'objet `XDM/1.0/DDM+<libelle> <NOM> <prenom> <date>`
- **ECO.2.2.1/2.2.2** — en-tetes `Message-ID`, `In-Reply-To`, `References` conformes
  RFC 5322 pour le threading

## Comportement attendu

1. **Depuis un message envoye** contenant un document medical, le professionnel peut
   declencher l'action "Annuler et remplacer"
2. Le systeme pre-remplit un nouveau message avec :
   - Les memes destinataires (To, Cc) que le message original
   - L'objet prefixe par `[Annule et remplace]` suivi de l'objet original
   - Si le message contient un IHE_XDM, l'objet complet est :
     `[Annule et remplace] XDM/1.0/DDM+<libelle> <NOM> <prenom> <date>`
   - Une mention dans le corps : "Ce message annule et remplace le message du
     {date original} ayant pour objet : {objet original}"
   - Les en-tetes `In-Reply-To` et `References` pointant vers le `Message-ID`
     original (threading RFC 5322)
3. Le professionnel attache le nouveau document et envoie
4. Le message original est marque visuellement comme "annule" dans la liste des
   messages envoyes

## Format de l'objet

| Cas | Objet du message de remplacement |
|---|---|
| Avec IHE_XDM | `[Annule et remplace] XDM/1.0/DDM+<libelle> <NOM> <prenom> <date>` |
| Sans IHE_XDM | `[Annule et remplace] <objet original>` |

A l'affichage (grace au masquage prefixe XDM, US task-002), le destinataire verra :
`[Annule et remplace] <libelle> <NOM> <prenom> <date>`

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/AnnuleEtRemplace.feature`

## Exigence Segur couverte

- AMBU.MSS/va1.02 — Nouvelle version avec mention "annule et remplace"

## References reglementaires

- REM Segur AMBU.MSS/va1.02
- Referentiel socle MSSante #2 v1.0.1 — ECO.2.1.1, ECO.2.1.3, ECO.2.2.1, ECO.2.2.2

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Action "Annuler et remplacer" disponible sur les messages envoyes contenant un document medical
- [ ] Pre-remplissage du nouveau message : memes destinataires, objet prefixe `[Annule et remplace]`, mention dans le corps avec date et objet originaux
- [ ] Si le message contient un IHE_XDM, l'objet respecte le format `[Annule et remplace] XDM/1.0/DDM+...` (conformite ECO.2.1.3)
- [ ] En-tetes `In-Reply-To` et `References` pointant vers le `Message-ID` original (RFC 5322)
- [ ] Le message original est marque visuellement comme "annule" dans la liste des envoyes
- [ ] Propriete `IsCancelled` (bool) ou equivalent ajoutee au modele `Mail` pour marquer les messages annules
- [ ] Blazor : bouton "Annuler et remplacer" sur le detail d'un message envoye avec document + indication visuelle des messages annules
- [ ] Angular : bouton "Annuler et remplacer" sur le detail d'un message envoye avec document + indication visuelle des messages annules
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- Envoyer un message avec un document CDA a un destinataire
- Ouvrir le message dans les envoyes → cliquer sur "Annuler et remplacer"
  - Verifier le pre-remplissage : memes destinataires,
    objet `[Annule et remplace] XDM/1.0/DDM+CR d'examens biologiques VIAL Paul 26/11/1978`,
    mention dans le corps
- Attacher un nouveau document et envoyer
  - Verifier que le message original est marque "annule" dans la liste des envoyes
- Cote destinataire : verifier que le message de remplacement affiche la mention
  `[Annule et remplace] CR d'examens biologiques VIAL Paul 26/11/1978` (prefixe XDM masque)
  et est lie au message original dans le fil de conversation
- Repeter sur les deux frontends
