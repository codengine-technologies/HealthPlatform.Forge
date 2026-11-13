**Résolu** le 2026-11-13 : reprise 2 lancée par l'humain (`/develop task-466 --reprise`), correctif appliqué
(HPRIM historique au nom d'un patient fictif propre, SEARCH-008 ajusté). Voir le Develop log du task file.

# task-466 — /e2e rouge : régression causée par la donnée de seed de la task

**Étape** : `/e2e` (2026-11-13). **Nature du blocage : régression** (voie Angular). Parité verte.
La chaîne est arrêtée avant `/review`, comme le veut la règle 13 : `/e2e` est en lecture seule et ne corrige rien.

## Ce qui est rouge

Voie Angular : 79 verts, **4 rouges** (après `retries: 1`) :

| Scénario | Test | Erreur |
|---|---|---|
| E2E-PATIENT-004 | patients — la vue « Mails du patient » reste ouverte et ses pages viennent du serveur | « le serveur sert le compte rendu de ce patient » : uid attendu absent de la 1re page, l'uid du compte rendu historique à sa place |
| E2E-SEARCH-008 | recherche — restreindre à un patient et à ses biologies anormales | « les deux biologies marquées anormales, et elles seules » : 3 au lieu de 2 |
| E2E-SEARCH-010 | recherche — reconnaître un résultat et ouvrir le dossier du patient | « le compte rendu du patient est dans ses messages » : élément introuvable |
| E2E-DASH-001 | tableau de bord — les widgets s'affichent | « le widget patients est rendu » : élément introuvable |

Traces : `Client/Angular/front/e2e/mss-e2e/out/test-results/*/error-context.md` (et `trace.zip`).

Voie mobile : **verte**, 62/62, au second passage. Le premier passage avait 7 rouges, tous
`ERR_CONNECTION_REFUSED` sur `localhost:8100` : le serveur de l'app et l'API sont tombés ensemble, sans trace. C'est
une panne d'outillage, pas une régression.

## Cause

C'est la donnée de seed ajoutée par la task. `cr-bio-historique` (E2E-BIO-007) réutilise le CDA de biologie du
corpus ANS, celui de `cr-bio-a-acquitter`. Il rattache donc un **second compte rendu au même patient fictif**, et
les parcours web de ce patient (pages, biologies anormales, dossier) le comptent.

Le lien de E2E-DASH-001 avec cette donnée est probable, mais **non démontré**.

## Correctif proposé (prêt, non appliqué : `/e2e` ne corrige pas)

Le compte rendu historique devient un **HPRIM synthétique au nom d'un patient fictif propre**, que nul autre message
ne porte (« HISTOE2E Dominique », un potassium signalé « H »). Il reste un résultat à acquitter, arrivé trois jours
avant la date de début du suivi, et ne touche plus aucune fiche des autres parcours.

- `E2eAttachmentKind.HistoricalHprim` ;
- `E2eSeedPlan.HistoricalHprimPatient` et `HistoricalHprimContent` ;
- le message `cr-bio-historique` passe à ce type, expéditeur « Laboratoire HPRIM E2E » ;
- son cas dans `E2eSeed.BuildMime` ;
- l'assertion de `E2eSeedPlanTests` ;
- la description `cr-bio-historique` du catalogue.

Les specs BIO-007 (mobile et Angular) ne changent pas : elles désignent le message par son uid et passent par
l'onglet Biologie et le panneau d'acquittement, que le HPRIM porte comme le CDA (cf. E2E-BIO-003).

Ce correctif a été écrit puis annulé pendant `/e2e` : les tests du seed et du catalogue passaient (32/32).

## Décision attendue

- **Reprise par la forge (recommandé)** : `/develop task-466 --reprise` avec ce correctif. La reprise rejoue d'abord
  les 4 scénarios rouges sur la voie Angular, puis la chaîne repasse par `/review --code`, `/e2e` (les deux voies
  complètes) et `/review`. Si E2E-DASH-001 reste rouge, il sera instruit à part.
- Ou une autre donnée historique de votre choix.
