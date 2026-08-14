# todo-task-263.md — Le harnais postule que les UID commencent à 1 : dès qu'une boîte a vécu, il rend des verdicts verts sans rien mesurer

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune.
**Priorité**: **2** — ce défaut a **invalidé deux campagnes distantes**. Il ne
casse pas le banc : il le fait mentir, ce qui est pire.

## Objective

Qu'une campagne puisse s'exécuter sur des boîtes dont les UID ne commencent pas à
1, ou qu'elle **refuse de démarrer** — mais qu'elle ne rende jamais un verdict
sur des messages inexistants.

## Ce qui est établi

`lib/uid-bands.js` calcule ses bandes par `start = 1 + batchIndex * enrichBatch`,
et `journeyReserves` code en dur `start: 1`. Les deux postulent qu'une boîte
commence à l'UID 1.

**Ce postulat n'est vrai que sur un maildir vierge.** Les UID IMAP ne sont
**jamais réutilisés** : purger une boîte par IMAP (`doveadm expunge`) supprime
les messages mais laisse le compteur avancer. Un re-seed repart donc au-delà.

**Mesuré le 2026-08-14** : les 500 boîtes du banc distant portaient les UID
**201 à 447** après une purge par IMAP suivie d'un re-seed. Aucun message n'avait
d'UID entre 1 et 10.

**Ce que le banc rendait dans cet état** — vérifié à la main avant de lancer la
campagne :

| Geste | Réponse | Réalité |
|---|---|---|
| `enrich/sync` sur les UID 1–3 | **HTTP 200 en 1,04 s** | 0 mail, 0 contenu, 0 document en base |
| Lecture des UID 1–5 | HTTP 200 | rien à lire, repli sur IMAP |

**Aucune erreur, aucun seuil franchi, aucun signal.** Un escalier complet aurait
rendu des verdicts **verts et flatteurs**. C'est mot pour mot ce qui s'est
produit lors de la première tentative distante à 500 : *« 8/11 vertes parce que
la base est vide »*.

**Le contournement existe mais ne corrige rien** : le Job
`maildir-purge-job.yaml` efface les répertoires de boîte et fait repartir les UID
de 1. Il remet le compteur à zéro ; il n'empêche pas le défaut de revenir à la
purge suivante.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que la purge suffit.** Elle a été faite le 2026-08-14, et le
  défaut reviendra à la prochaine boîte qui aura vécu.
- **Ne pas présumer qu'un décalage fixe suffit.** Deux boîtes peuvent avoir des
  UID de départ différents — trois boîtes du banc en portaient déjà, du fait d'un
  calibrage. Un décalage global les traiterait toutes comme la plus basse.
- **Ne pas se contenter d'un paramètre.** Un `UID_BASE` mal réglé reproduit le
  défaut en silence. **Le refus de démarrer est au moins aussi important que le
  décalage.**

## Ce que la US doit livrer

Deux choses, et la seconde est la plus importante :

1. **Un décalage d'UID**, de sorte que les bandes visent les messages qui
   existent réellement.
2. **Un contrôle au démarrage** : le `setup()` vérifie que la bande visée
   **existe** dans la boîte, et **refuse le tir** avec un message qui nomme la
   cause et le geste — comme le fait déjà le contrôle de budget du parcours, qui
   a refusé une campagne mal dimensionnée le 2026-08-14 **avant** de brûler deux
   heures de banc. C'est le modèle à suivre.

## Definition of Done

- [ ] Build passe, auto-tests du harnais verts (`selftest.sh`) — **y compris les
      tests JS**, ce qui suppose Node disponible ; un SKIP n'est pas un succès
- [ ] Les bandes d'UID (`uid-bands.js` **et** `journey-model.js`) partent d'une
      base **paramétrable**, défaut inchangé à 1
- [ ] Le `setup()` **refuse le tir** quand la bande visée n'existe pas dans les
      boîtes, avec un message qui **nomme la cause et le geste** — sur le modèle
      du contrôle de budget
- [ ] Le refus est **éprouvé** : un test le déclenche, et le message est vérifié
- [ ] Le contrôle porte sur **plusieurs boîtes**, pas une seule — des boîtes
      peuvent différer entre elles
- [ ] Le skill `loadtest-skill` documente le contrôle et le geste de purge
      (`maildir-purge-job.yaml`), en disant **pourquoi `kubectl exec rm -rf`
      échoue** (répertoires `drwx------ 1000:1000`, `root_squash` NFS)
- [ ] **Contre-épreuve** : un tir court sur des boîtes à UID décalés rend des
      chiffres **non nuls** et cohérents, là où il rendait des verdicts verts
      sans travail

## Manual Test Plan

- Sur le banc distant, relever la base d'UID d'une boîte :
  `python` + `imaplib`, `FETCH 1 (UID)` — ou `doveadm`
- Lancer un tir court **sans** décalage sur des boîtes décalées : il doit
  **refuser de démarrer** et nommer la cause
- Relancer **avec** le décalage : le tir démarre, et le nombre de messages
  enrichis doit **égaler** le nombre soumis
- Contrôle de non-régression : sur un maildir vierge (UID à partir de 1), le
  comportement par défaut est **inchangé**

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de banc
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : sans objet — outillage de test, données 100 % synthétiques
- **Interop CI-SIS** : sans objet
- **Habilitations** : sans objet
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : inchangé
- **Hébergement HDS** : sans objet — le harnais ne tourne jamais en production
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : feat/task-263-uid-base-refus
- `dtos-mss` (pushed, auto-inclus) : feat/task-263-uid-base-refus — aucune modification attendue
