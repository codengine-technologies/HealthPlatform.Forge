# task-456 — /e2e rouge : E2E-TAG-002 et E2E-TAG-003 en voie Angular (défaut du test)

**Étape** : `/e2e` (après la revue anticipée APPROVED au passage 3, `/sonar` vert, lint propre).
**Nature du blocage** : régression **apparente** sur la voie Angular. Le défaut est dans le **test e2e weda2** écrit par
la task ; le produit n'est pas en cause.

## Constat

- **Voie mobile** : verte. 66 tests, 0 flaky, 0 rouge. E2E-TAG-002 et E2E-TAG-003 passent.
- **Voie Angular** : 85 verts, **2 rouges**, E2E-TAG-002 et E2E-TAG-003, aux deux essais. Message :
  « … est dans la vue BIOLOGIE, côté serveur », attente de 180 s épuisée.
- Parité verte sur les deux clients. Démontage complet.

## Cause

- Dans weda2, l'aide `waitForTagView` (`e2e/mss-e2e/specs/functional.e2e.ts`, vers la ligne 6630) attend la vue
  BIOLOGIE côté serveur avant que l'écran n'ait affiché la boîte. Elle ne relit que les en-têtes (`mailBySubject`).
- Personne ne demande l'**analyse** du message, alors que le tag Biologie est décidé à l'analyse (`enrich`). Le tag
  n'arrive donc jamais.
- L'aide mobile du même scénario (`OtherDevice.waitForTags`) appelle `POST …/emails/enrich/sync`, comme l'app qui
  affiche le message. C'est pourquoi la voie mobile est verte sur le même backend.

Prévention déjà écrite : `conventions/e2e.md` § `etat-decide-a-l-analyse-attendu-cote-serveur`.

## Correctif proposé (petit, test seulement)

- Dans `e2e/mss-e2e/support/e2e-backend.ts`, ajouter à `OtherDevice` une méthode qui fait analyser un message par son
  uid (`enrich/sync`), sur le modèle de l'aide mobile.
- L'appeler dans `waitForTagView` avant de lire la vue.
- Rejouer d'abord les deux seuls scénarios (`--serve-only` puis `playwright --grep "E2E-TAG-00[23]"`), puis la voie
  Angular complète à `/e2e`.

## Pourquoi la forge s'arrête

- `/e2e` est bloquant sans exemption (un parcours rouge arrête la chaîne, règle 13).
- La task a déjà consommé ses **2 reprises** automatiques (`**Reprises**: 2`).

## Décision attendue

Autoriser une reprise hors plafond limitée à ce correctif de test :

```
/develop task-456 --reprise
```

Sinon, une autre décision : corriger à la main, ou poser une quarantaine (qui doit citer une task de correction).
