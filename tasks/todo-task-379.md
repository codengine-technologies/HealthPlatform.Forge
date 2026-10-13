# todo-task-379.md — Contacts et annuaire : une fiche enregistrée garde toutes ses adresses, et seules des adresses MSSanté sont importées

**Repos**: client-angular, api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — des adresses de messagerie de santé disparaissent à l'enregistrement d'un contact ; une adresse non MSSanté de l'annuaire peut devenir l'adresse principale proposée à la rédaction ; une seule erreur réseau rend la recherche muette jusqu'au rechargement.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-56, ANG-57, ANG-58**).

## Ce qui est établi

- **ANG-57** — `mss-contacts.component.ts:409-464` n'édite que `mssAddresses[0]` et renvoie l'instantané chargé à l'affichage ; `ContactRepository.cs:143-246` supprime puis réinsère adresses, étiquettes et groupes : les adresses secondaires et les changements concurrents (enrichissement par l'annuaire, autre onglet) sont perdus. Aucun contrôle de version.
- **ANG-58** — `mss-contacts.component.ts:829-858` enregistre tous les e-mails FHIR comme adresses MSSanté ; `FhirBundleParser.cs:270-275, 384-391` garde tous les `telecom` de type e-mail. *Probable* (hypothèse : l'annuaire expose des e-mails non MSSanté).
- **ANG-56** — `patient-search.component.ts:59-77` (`catchError` après `switchMap`) et `mss-contacts.component.ts:1003-1022` : une erreur HTTP termine le flux de recherche ; toute frappe suivante reste sans effet (« Aucun patient trouvé »). Le chargement initial des patients du jour n'est pas annulé.

## Objective

Qu'enregistrer un contact **ne fasse perdre aucune** de ses adresses, étiquettes ou appartenances, que l'import depuis l'annuaire ne retienne **que** des boîtes MSSanté, et que les recherches de patients et de contacts survivent à une erreur passagère.

### Périmètre

1. **Édition complète** de la liste des adresses MSSanté d'un contact ; mise à jour partielle (PATCH) ou contrôle de version côté api-mail (refus d'un enregistrement fondé sur un état périmé).
2. **Annuaire** : seules les boîtes MSSanté sont retenues (type de BAL ou extension de l'annuaire, domaine de l'espace de confiance), côté serveur ; l'utilisateur voit ce qu'il importe.
3. **Recherches** : `catchError` dans le `switchMap`, message d'erreur, recherche toujours active ; chargement initial annulé à la première frappe.

## Definition of Done

- [ ] Build et tests verts : weda2, api-mail
- [ ] Test d'intégration de bout en bout pour l'enregistrement d'un contact à deux adresses MSSanté dont on modifie le téléphone : les deux adresses sont dans la réponse et en base ; un enregistrement fondé sur un état périmé est refusé (409), vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour la recherche dans l'annuaire : un praticien portant une adresse MSSanté et un e-mail ordinaire ne renvoie que l'adresse MSSanté dans le champ des boîtes, vu rouge (règle 1b)
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] l'écran d'édition affiche et renvoie toutes les adresses du contact
  - [ ] recherche en 500 puis nouvelle frappe : la recherche repart et affiche ses résultats
- [ ] Scénario E2E-CONTACT-002 versionné : enregistrer un contact à deux adresses les conserve toutes deux (angular `requis` ; mobile : `requis` si l'édition de contact existe sur mobile, à confirmer au `/start`)
- [ ] Aucune adresse ajoutée aux journaux

## Manual Test Plan

1. Contact importé de l'annuaire avec deux adresses MSSanté : modifier son téléphone, enregistrer → les deux adresses sont toujours là.
2. Rechercher dans l'annuaire un praticien qui a aussi un e-mail ordinaire → seules ses adresses MSSanté sont proposées à l'import.
3. Couper le réseau pendant une recherche de patient, le rétablir, retaper → les résultats s'affichent.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable (contacts professionnels ; la recherche patient ne change pas de critères)
- **Authentification PS** : inchangée
- **Habilitations** : identification des correspondants par l'annuaire santé (RPPS) inchangée
- **Interop CI-SIS** : FHIR R4 — annuaire santé (`Practitioner`, `PractitionerRole`, `telecom`) : seules les boîtes MSSanté sont retenues
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : annuaire santé (RPPS)
- **Hébergement HDS** : non applicable — données de professionnels
- **AIPD / impact RGPD** : inchangé
- **MSSanté** : adresses de l'espace de confiance seulement, pour qu'aucune donnée de santé ne parte hors de celui-ci
