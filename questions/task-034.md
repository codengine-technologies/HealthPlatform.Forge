# questions/task-034.md — Version supprimee (INT.18)

**Task**: task-034 — Conformite INT.18 : detection doublons CDA par id/setId/versionNumber
**Date**: 2026-05-07
**Status**: open

## Question

INT.18 mentionne qu'un document CDA peut arriver sous forme de **version
supprimee** (le document original est annule/obsolete par l'emetteur). Le CDA
peut porter un `statusCode` indiquant la suppression (par exemple
`statusCode@code = "obsolete"` ou `"aborted"`).

**Quel comportement adopter quand le systeme recoit une version supprimee ?**

### Option A — Suppression/masquage automatique

Le document existant est automatiquement masque (soft-delete) ou marque comme
"supprime par l'emetteur". Le professionnel voit un indicateur mais le
document n'apparait plus dans la liste active.

**Avantage** : conformite stricte, pas d'action manuelle requise.
**Risque** : un document deja consulte/integre dans le dossier patient
disparait sans validation humaine.

### Option B — Signalement au professionnel

Le document existant est signale comme "demande de suppression recue" avec un
badge visuel. Le professionnel decide s'il masque ou conserve le document.

**Avantage** : le professionnel garde le controle, pas de perte de donnee
involontaire.
**Risque** : si le professionnel ignore le signalement, le document obsolete
reste visible.

### Option C — Hybride

Signalement au professionnel (option B) avec un delai configurable au-dela
duquel le systeme applique automatiquement le masquage (option A).

## Contexte

La task-034 couvre la detection par `id`, `setId`, `versionNumber` mais la
gestion des versions supprimees est un sous-cas specifique qui necessite une
decision PO. Le reste de la task peut avancer independamment — la gestion des
versions supprimees peut etre implementee en follow-up si la decision n'est
pas tranchee immediatement.
