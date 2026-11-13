# E024 — Messagerie premium : traiter, déléguer, boucler

> **Statut** : ✅ 1 feature livrée et validée — les 12 autres features prévues ont été **retirées du backlog** le
> 2026-11-12 (décision humaine : développements non engagés ; tasks 454 à 464 et 466 supprimées)
> **Version** : 0.1
> **Auteur** : PO forge (task-453)
> **Modèle** : task-driven
> **Dernière mise à jour** : 2026-11-12
> **Vue ingénierie** : [E024-Changelogs.md](E024-Changelogs.md)

---

<!-- toc:start — section générée par /tech-writer ; ne pas éditer manuellement -->

## Sommaire

- [1. Vision](#1-vision)
- [2. Objectifs métier](#2-objectifs-métier)
- [3. Acteurs concernés](#3-acteurs-concernés)
- [4. Features de l'EPIC](#4-features-de-lepic)
- [5. Workflow entre Features](#5-workflow-entre-features)
- [6. Règles métier transverses](#6-règles-métier-transverses)
- [7. Contraintes et hypothèses](#7-contraintes-et-hypothèses)
- [8. Critères d'acceptation de l'EPIC](#8-critères-dacceptation-de-lepic)
- [9. Hors périmètre](#9-hors-périmètre)
- [État de couverture (2026-11-12)](#état-de-couverture-2026-11-12)
- [Synthèse fonctionnelle des changelogs](#synthèse-fonctionnelle-des-changelogs)

<!-- toc:end -->

---

## 1. Vision

La messagerie ne se contente plus de recevoir et d'envoyer. Elle aide le cabinet à **traiter** ce qui arrive, à
**déléguer** ce qui revient à quelqu'un d'autre, et à **boucler** chaque échange jusqu'au bout : un résultat de
biologie acquitté puis communiqué au patient, un courrier envoyé dont on sait qu'il est arrivé et a été lu, une
demande restée sans réponse qui revient d'elle-même.

Tout ce que le cabinet décide sur un message — acquittement, « traité », report, attribution, note, suivi — est une
trace de travail. Ces traces appartiennent à la boîte, portent le nom de la personne qui les a posées, et ne
disparaissent jamais parce que le message a été rangé ailleurs, depuis la plateforme ou depuis un autre logiciel.

*Source : analyse fonctionnelle des manques de la messagerie du 2026-11-11.*

---

## 2. Objectifs métier

- Le praticien voit ce qui **reste à traiter**, pas seulement ce qui n'est pas lu.
- Le cabinet se **répartit** le travail d'une même boîte sans échange hors de la messagerie.
- Aucun résultat de biologie ne se perd entre sa lecture et sa communication au patient.
- Le praticien sait si son message est **arrivé**, a été **lu**, ou pourquoi il a **échoué**.
- Une trace de travail posée sur un message n'est **jamais perdue**, quoi qu'il arrive au message.

---

## 3. Acteurs concernés

- **Le médecin titulaire** de la boîte.
- **Les confrères membres** d'une boîte organisationnelle.
- **La secrétaire ou l'assistante délégataire**, qui travaille dans la boîte du médecin.
- **Le patient**, destinataire d'un envoi par Mon espace santé.
- **L'équipe produit**, qui suit la charge de la messagerie sans voir aucune donnée de santé.

---

## 4. Features de l'EPIC

> Le bilan d'avancement par feature (statut, couverture, tasks contributives) est consigné en fin de document, dans
> la section *État de couverture*.

| Fonctionnalité | Ce que le praticien peut faire | Tasks | Statut |
|---|---|---|---|
| Un acquittement ne disparaît jamais | Retrouver l'acquittement d'un compte rendu, sa note, son auteur et le patient rattaché à la main, même après que le message a été rangé depuis un autre logiciel, supprimé puis restauré, ou relu après un incident de la messagerie | task-453 | ✅ Livrée et validée |

---

## 5. Workflow entre Features

> ⚠️ Vision d'origine, **non engagée** : hors « Un acquittement ne disparaît jamais », les étapes de ce parcours
> (marquer traité, « À traiter par », « À revoir le », suivi d'acheminement, relance, suivi de biologie) ont été
> retirées du backlog le 2026-11-12.

Le parcours d'un message dans le cabinet, tel que l'EPIC l'envisageait :

```mermaid
flowchart LR
    A[Un message arrive] --> B{Sa nature}
    B -->|Biologie| C[Lire le résultat<br/>et l'acquitter]
    B -->|Courrier, patient, pour info| D[Le lire]
    C --> E[Décider : rien à faire,<br/>revoir le patient]
    E --> F[Suivi daté jusqu'au<br/>résultat communiqué]
    D --> G{Qui le traite ?}
    G -->|Moi| H[Répondre, noter,<br/>marquer traité]
    G -->|Un autre| I[À traiter par…]
    G -->|Plus tard| J[À revoir le…]
    H --> K[Suivi d'acheminement,<br/>relance sans réponse]
    F --> L[Traces de travail<br/>conservées, jamais perdues]
    H --> L
    I --> L
    J --> L
```

Toutes les traces de travail de ce parcours reposent sur le socle posé par la première feature (task-453) : elles
restent attachées au document ou au message, même quand celui-ci est déplacé, purgé puis relu, ou supprimé puis
restauré.

---

## 6. Règles métier transverses

| Règle | Énoncé | Statut |
|---|---|---|
| Une trace de travail ne disparaît jamais | Un acquittement, un rattachement manuel ou un état de travail survit à tout ce qui fait disparaître puis revenir un message ; il est conservé, même invisible, tant que le même document ne revient pas | ✅ Implémenté pour l'acquittement et le rattachement manuel (task-453) |
| Rien d'inventé | Une trace n'est rendue à un message que si l'identité du document est certaine ; dans le doute (deux copies du même document), rien n'est rendu et la décision est tracée | ✅ Implémenté (task-453) |
| Une nouvelle version est un nouveau document | Une nouvelle version d'un compte rendu n'hérite pas des acquittements de l'ancienne | ✅ Implémenté (task-453) |
| Tout acte est imputé à son auteur réel | Chaque trace porte la personne qui l'a posée (titulaire, membre, délégataire), y compris quand elle revient sur un message rangé ailleurs ; ce que la plateforme fait seule est tracé comme acte système | ✅ Implémenté pour l'acquittement et le rattachement manuel (task-453) |

---

## 7. Contraintes et hypothèses

- Les traces de travail appartiennent à la **boîte** : toutes les personnes rattachées à la boîte les voient (règle de
  la boîte partagée, EPIC E020).
- Le rattachement à la main d'un document à un patient n'est possible que pour un document **sans INS** ; un document
  porteur d'une INS suit l'identité de référence.
- Les traces sont conservées aussi longtemps que le journal d'accès aux données de santé.

---

## 8. Critères d'acceptation de l'EPIC

- [ ] Toutes les features du §4 sont livrées et validées par l'humain.
- [x] Un acquittement de biologie et un rattachement manuel survivent au rangement d'un message depuis un autre
      logiciel (vérifié automatiquement sur l'application mobile et sur l'application web, task-453).
- [ ] Le praticien voit, en ouvrant sa boîte, ce qui reste à traiter et par qui.

---

## 9. Hors périmètre

- **La mesure de la charge et de l'usage de la messagerie** (volumes, délais, personnes connectées, boîtes et
  délégataires, plages horaires) : abandonnée dans l'application le 2026-11-12, sur décision humaine. Elle sera
  produite plus tard **hors de l'application**, par un traitement planifié qui établit un rapport journalier.
- Les étiquettes d'un message : elles se recalculent lorsqu'il revient.
- Les marques « lu » ou « signalé » posées depuis un autre logiciel : sujet distinct.
- Les acquittements et rattachements manuels posés **avant** la mise en service de cette protection ne sont pas
  protégés : seuls les comptes rendus reçus ensuite le sont.

---

## État de couverture (2026-11-12)

| Feature | Statut | Couverture | Tasks contributives |
|---|---|---|---|
| Un acquittement ne disparaît jamais | ✅ Livrée et validée | 100 % | task-453 |

**Couverture EPIC consolidée : 100 %** de ce qui est retenu (1 feature livrée et validée). Les 12 autres features
prévues ont été retirées du backlog le 2026-11-12, sans développement engagé.

---

## Synthèse fonctionnelle des changelogs

### Fonctionnalités métier

- **v0.1 — Un acquittement ne disparaît jamais.** Quand un compte rendu de biologie acquitté est rangé depuis le
  webmail de l'opérateur, purgé puis relu après un incident de la messagerie, ou supprimé puis restauré, il revient
  avec son acquittement intact : action, note, auteur et heure d'origine. Il ne revient plus « à acquitter ». Le
  patient rattaché à la main à un document sans INS est retrouvé de la même façon (task-453).

### Conformité réglementaire

- **v0.1 — Imputabilité.** Un acquittement qui revient garde l'auteur réel qui l'avait posé, délégataire compris. Le
  fait de le rendre au message est tracé au journal comme acte de la plateforme, sans personne, sans INS ni nom de
  patient, et conservé aussi longtemps que les autres accès aux données de santé (task-453).

### Sécurité

- **v0.1 — Aucune perte silencieuse.** Un message supprimé pour de bon ne détruit plus la trace de prise de
  connaissance d'un résultat. Dans le doute sur l'identité d'un document, la plateforme ne rattache rien et le trace
  (task-453).

### Technique / observabilité (sans impact utilisateur direct)

- **v0.1 — Socle commun des traces de travail.** Le modèle qui protège l'acquittement est celui que suivront tous les
  états de travail de l'EPIC (traité, report, attribution, notes, suivis). Un parcours automatique supplémentaire
  vérifie désormais ce cas sur les deux applications (task-453).

---

*Document vivant, reconstruit par la forge à chaque fin de cycle d'une task de l'EPIC.*
