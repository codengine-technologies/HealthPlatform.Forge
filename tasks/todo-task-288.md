# todo-task-288.md — Fiabiliser la vérification de révocation des certificats MSSanté (OCSP et CRL)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009

## Objective

La vérification de révocation OCSP des certificats serveur MSSanté est
**structurellement hors service**. Le point d'accès de l'IGC-Santé qui publie le
certificat d'autorité intermédiaire répond `403 Forbidden` à chaque tentative, et
l'application le re-sollicite à **chaque poignée de main TLS** — donc à chaque
ouverture de dossier et à chaque envoi.

Le service ne s'en rend pas compte parce que le repli CRL fonctionne :

```
[ValidateRevocation] OCSP validation failed, falling back to CRL. Errors: Error processing the AIA extension.
[ValidateRevocation] Server certificate is valid (CRL fallback check passed).
```

Rien n'est cassé fonctionnellement aujourd'hui. Mais **le dernier filet est déjà
en service**, et la posture retenue en arbitrage (grâce de 4 h sur cache périmé
puis fail-close) suppose que la CRL soit un secours occasionnel, pas le mode
nominal. Le jour où la CRL est indisponible à son tour — même hébergeur, même
exposition — les connexions IMAP et SMTP sont refusées sous 4 h.

Cette US remet OCSP en service, cesse de maltraiter le point d'accès de l'ANS,
et applique le même durcissement au chemin CRL pour qu'il redevienne un vrai
secours.

## Constat (mesuré le 2026-09-01)

**Ce n'est ni nouveau, ni lié à la conteneurisation.** La même erreur est
présente en mode projet Windows (`MachineName: WEDA-0138`, chemins
`D:\TechWatch\…`) à **15:50**, soit 3 h 40 avant le premier démarrage en
conteneur (`MachineName: 49c0f3327755`, 19:29). Elle n'avait simplement jamais
été regardée.

**Le point d'accès limite le débit par IP source, très agressivement.** Testé à
la main sur `http://igc-sante.esante.gouv.fr/AC/ACI-EL-ORG.cer` :

| Essai | Résultat |
|---|---|
| 1ʳᵉ série, sans en-tête `User-Agent` | **200**, 1856 octets |
| 1ʳᵉ série, `User-Agent` de navigateur | **200** |
| 2ᵉ série une minute plus tard, **toutes** variantes | **403** |

Ce n'est donc **pas** un filtrage sur `User-Agent` — les combinaisons qui
passaient échouent au second passage. Quelques requêtes suffisent à déclencher le
blocage, qui persiste ensuite.

**L'application entretient elle-même son blocage.** Trois défauts se composent :

1. **Aucun cache négatif.** Le cache (mémoire puis Redis partagé, 24 h) n'est
   alimenté que par les **succès**. Un échec n'est pas mémorisé, donc la
   poignée de main suivante retente — et maintient le blocage.
2. **Aucun backoff.** Deux tentatives immédiates, puis on recommence au
   handshake suivant. Relevé dans les journaux : 20:00:20, 20:03:24, 20:03:54,
   20:08:00, 20:09:01, 20:09:39.
3. **Aucune sérialisation.** Rien ne garantit qu'un seul téléchargement soit en
   vol pour une même URL : N poignées de main simultanées font N téléchargements
   du même octet.

**Le volume nominal est pourtant dérisoire.** Le certificat d'AC pèse
1856 octets, il est mis en cache 24 h, et il change tous les plusieurs
années. Le régime normal est **un téléchargement par jour et par autorité**.
Tout le problème vient de ce que, l'échec n'étant jamais mémorisé, ce régime
n'est jamais atteint.

**Le chemin CRL a exactement la même forme** — client HTTP nommé non
enregistré, réessai borné, mise en cache des seuls succès. Il ne tient que
parce qu'il réussit encore, et qu'un succès lui vaut 24 h de cache.

**Point d'attache manquant.** Les clients nommés `"OcspClient"` et `"CrlClient"`
ne sont **jamais enregistrés** — `CreateClient` rend un client par défaut, sans
politique de résilience ni délai propre. C'est là que doit se poser le
durcissement.

## Règles métier

1. **La révocation reste vérifiée.** Cette US ne relâche aucun contrôle : elle
   restaure le chemin nominal (OCSP) et consolide le repli (CRL). La posture
   arbitrée — grâce de 4 h sur cache périmé, puis fail-close ; certificat révoqué
   refusé immédiatement et sans grâce — est **inchangée**.

2. **Un échec de téléchargement est mémorisé.** Une indisponibilité du point
   d'accès n'est pas réessayée à la poignée de main suivante. La durée de
   mémorisation est courte devant le cache de succès, pour qu'un rétablissement
   soit repris rapidement.

3. **Les réessais sont espacés.** Après un échec, les tentatives suivantes sont
   progressivement espacées plutôt que répétées à chaque handshake. L'objectif
   est explicite : **cesser d'entretenir le blocage** et laisser la limitation de
   débit se lever.

4. **Un seul téléchargement en vol par ressource.** Des poignées de main
   simultanées qui ont besoin de la même ressource attendent le même
   téléchargement. En régime établi, l'application ne sollicite l'ANS qu'**une
   fois par jour et par autorité**.

5. **Le certificat d'AC intermédiaire est livré avec l'application.** Il amorce
   le cache au démarrage, sans aucun accès réseau. Démarrage à froid immédiat et
   indépendant de la disponibilité de l'ANS.

6. **La graine ne remplace pas le téléchargement.** Toute autorité inconnue de
   la graine reste résolue en ligne, selon les règles 2 à 4. Un oubli de mise à
   jour de la graine dégrade donc les performances, **jamais la correction** :
   c'est ce qui rend la règle 5 sans risque.

7. **Le même traitement s'applique aux deux chemins**, OCSP et CRL. Le repli
   doit être aussi robuste que le chemin nominal, puisqu'il est le dernier
   rempart avant le fail-close.

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 échec)
- [ ] Les clients HTTP de révocation sont enregistrés explicitement, avec délai
      et politique de résilience propres
- [ ] Test : deux échecs consécutifs ne produisent **pas** deux salves de
      téléchargement — le second est servi par la mémorisation de l'échec
      (règle 2)
- [ ] Test : après un échec, les tentatives sont espacées et non répétées à
      chaque sollicitation (règle 3)
- [ ] Test : N demandes concurrentes sur la même ressource déclenchent **un
      seul** téléchargement (règle 4)
- [ ] Test : au démarrage, la vérification de révocation fonctionne **sans
      aucun accès réseau** vers l'ANS, grâce à la graine (règle 5)
- [ ] Test : une autorité absente de la graine est bien résolue en ligne
      (règle 6 — c'est le test qui prouve que la graine n'a pas introduit
      d'angle mort)
- [ ] Test : un certificat révoqué reste refusé immédiatement, sans grâce
      (non-régression de la posture arbitrée, règle 1)
- [ ] Test : la grâce de 4 h puis le fail-close sont inchangés
      (non-régression, règle 1)
- [ ] Le durcissement couvre les deux chemins, OCSP **et** CRL (règle 7)
- [ ] La provenance et la date de la graine sont documentées, ainsi que la
      procédure de mise à jour à la rotation de l'autorité
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. **Démarrage à froid, sans réseau vers l'ANS.** Vider le cache Redis
   (`docker exec … redis-cli FLUSHALL`), démarrer le backend, puis se connecter
   et ouvrir la boîte de réception. **Attendu** : la vérification de révocation
   aboutit, et **aucune** requête vers `igc-sante.esante.gouv.fr` n'apparaît dans
   les journaux. C'est le test central de la US.
2. **Régime établi.** Naviguer une dizaine de minutes (dossiers, ouverture de
   messages, un envoi). **Attendu** : dans Seq, filtrer sur
   `SourceContext like '%OcspValidationService%'` — aucune erreur, et au plus un
   téléchargement par autorité.
3. **Point d'accès indisponible.** Simuler l'indisponibilité (règle de pare-feu
   sortante, ou pointage sur une URL qui renvoie 403). Ouvrir la boîte de
   réception plusieurs fois de suite. **Attendu** : le service **ne repart pas**
   en téléchargement à chaque sollicitation ; les tentatives s'espacent ; la
   connexion aboutit toujours via le cache ou la CRL.
4. **Concurrence.** Cache vidé, ouvrir simultanément plusieurs onglets qui
   chargent la boîte de réception. **Attendu** : un seul téléchargement par
   ressource dans les journaux, pas un par onglet.
5. **Non-régression de la posture.** Vérifier qu'un certificat révoqué est
   toujours refusé immédiatement, et que le comportement au-delà de la fenêtre
   de grâce de 4 h est inchangé.
6. **Rotation de l'autorité.** Renommer la graine pour simuler une autorité
   inconnue. **Attendu** : la résolution en ligne prend le relais (règle 6),
   sans échec fonctionnel.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors périmètre fonctionnel DSR — correctif de robustesse sur
  un socle MSSanté déjà référencé
- **Exigences DSR honorées** : aucune exigence DSR fonctionnelle nouvelle. La US
  restaure le respect effectif de la **PGSSI-S § cryptographie et validation des
  certificats** et du Référentiel socle MSSanté #2 §2.1.1.2.3 (vérification du
  certificat serveur présenté par l'Opérateur, certificat IGC Santé). **Le
  rattachement DSR précis est à confirmer avec le référent Ségur** — je ne cite
  pas de code d'exigence que je n'ai pas vérifié.
- **INS** : non applicable — la validation de certificat ne manipule aucune
  donnée patient.
- **Authentification PS** : PSC / e-CPS, inchangé. La US porte sur
  l'authentification **du serveur MSSanté**, pas sur celle du praticien.
- **Habilitations** : non applicable.
- **Interop CI-SIS** : non applicable — aucun échange métier.
- **Tracé PGSSI-S** : à journaliser — échec de résolution d'une autorité, entrée
  en réessai espacé, usage de la graine au démarrage, entrée en fenêtre de grâce,
  fail-close. Ces évènements sont ceux que `todo-task-287` doit rendre
  mesurables ; les deux US se complètent sans se recouvrir (287 **compte**,
  288 **corrige**).
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — l'API héberge des DSCP. La US ne crée aucun
  nouveau flux de données de santé ; la graine est un certificat d'autorité
  publique.
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle traitée.
- **Sécurité** : point de vigilance central — **aucun assouplissement du
  contrôle de révocation n'est acceptable au prétexte de la robustesse.** Un
  échec de résolution ne doit jamais devenir un succès implicite. La graine ne
  fait qu'éviter un téléchargement ; elle ne dispense d'aucune vérification, et
  un certificat révoqué reste refusé sans grâce.

## Note — origine du constat

Défaut relevé le 2026-09-01 en analysant les journaux Seq après le passage en
profil conteneur. L'humain l'a signalé comme « une erreur jamais vue en Aspire » ;
l'instruction a montré qu'elle était **présente dès le mode projet le même jour**,
et probablement bien avant. C'est exactement le type d'angle mort que
`todo-task-287` doit supprimer : un défaut réglementaire silencieux, découvert
par lecture de journaux et non par un signal.
