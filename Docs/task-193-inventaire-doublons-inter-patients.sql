-- =============================================================================
-- task-193 — Inventaire des documents masqués à tort (doublon inter-patients)
-- =============================================================================
--
-- LECTURE SEULE. Aucune écriture, aucune correction. La remédiation touche des
-- données de santé : elle relève d'un arbitrage humain et d'une task dédiée,
-- pas de cette requête.
--
-- CE QUE LA REQUÊTE CHERCHE
-- -------------------------
-- Un document marqué doublon (`DuplicateOfId` renseigné) dont le patient
-- DIFFÈRE de celui du document référencé. C'est la signature exacte du défaut :
-- la détection comparait les identifiants de document sans aucun prédicat de
-- patient, et un identifiant fabriqué (« _ », produit quand l'émetteur omet la
-- balise <id> du CDA) faisait se ressembler tous les documents non identifiés.
--
-- POURQUOI CES LIGNES COMPTENT
-- ----------------------------
-- Toutes les requêtes du dossier patient écartent les doublons
-- (`DuplicateOfId IS NULL OR DuplicateRejected`). Un document listé ici est donc
-- ABSENT du dossier de son patient et du tableau de bord — visible seulement
-- dans la boîte de réception, avec un signal de doublon pointant sur le document
-- d'un autre patient. Un document clinique masqué est un risque de prise en
-- charge, pas un désagrément d'affichage.
--
-- PORTÉE
-- ------
-- Une base par praticien : cette requête s'exécute sur CHAQUE base praticien,
-- séparément. Un résultat vide sur une base ne dit rien des autres.
--
-- CONFIDENTIALITÉ
-- ---------------
-- La requête ne rend NI INS, NI nom, NI contenu clinique. Elle rend des
-- identifiants techniques, un booléen d'égalité d'INS, des horodatages et le
-- dossier. C'est suffisant pour dénombrer et pour retrouver les lignes ensuite,
-- et cela permet de sortir le résultat d'un environnement de production sans
-- transporter de donnée de santé. Le rapprochement nominatif, s'il est
-- nécessaire, se fait dans la base, par le praticien ou sous sa responsabilité.
-- =============================================================================

SELECT
    doublon."Id"                            AS document_masque_id,
    doublon."MailId"                        AS mail_du_document_masque,
    doublon."FolderPath"                    AS dossier,
    doublon."CreatedAt"                     AS recu_le,
    reference."Id"                          AS document_reference_id,
    reference."CreatedAt"                   AS reference_recue_le,

    -- Le motif du rapprochement, sans révéler la valeur quand elle est
    -- signifiante : on distingue seulement l'identifiant fabriqué historique
    -- des autres, parce que c'est lui qui désigne le cas « émetteur non
    -- conforme » que task-193 corrige à la source.
    CASE
        WHEN doublon."DocumentId" IS NULL              THEN 'identifiant absent'
        WHEN doublon."DocumentId" = '_'                THEN 'identifiant fabrique (_)'
        WHEN btrim(doublon."DocumentId") = ''          THEN 'identifiant vide'
        ELSE 'identifiant renseigne'
    END                                     AS nature_identifiant,

    -- Faux dans tous les cas remontés, par construction du WHERE ; la colonne
    -- est là pour que le résultat se lise sans revenir au prédicat.
    (doublon."Ins" IS NOT DISTINCT FROM reference."Ins")
                                            AS meme_patient,

    doublon."DuplicateRejected"             AS doublon_rejete_par_le_praticien

FROM "MailMedicalDocuments" AS doublon
JOIN "MailMedicalDocuments" AS reference
     ON reference."Id" = doublon."DuplicateOfId"

WHERE doublon."DuplicateOfId" IS NOT NULL
  -- IS DISTINCT FROM, et non <> : deux INS nuls doivent compter comme
  -- « indéterminé », pas comme « différents » — et surtout, `NULL <> NULL`
  -- rend NULL, donc un simple <> écarterait silencieusement les cas où l'un
  -- des deux INS manque, qui sont précisément les plus suspects.
  AND doublon."Ins" IS DISTINCT FROM reference."Ins"

ORDER BY doublon."CreatedAt" DESC;


-- =============================================================================
-- Dénombrement — à exécuter en premier pour savoir s'il y a matière
-- =============================================================================
--
-- SELECT
--     count(*)                                          AS documents_masques_a_tort,
--     count(*) FILTER (WHERE doublon."DuplicateRejected") AS deja_rejetes_par_le_praticien,
--     count(*) FILTER (WHERE doublon."DocumentId" = '_' OR doublon."DocumentId" IS NULL
--                        OR btrim(doublon."DocumentId") = '')
--                                                       AS dus_a_un_identifiant_absent,
--     min(doublon."CreatedAt")                          AS plus_ancien,
--     max(doublon."CreatedAt")                          AS plus_recent
-- FROM "MailMedicalDocuments" AS doublon
-- JOIN "MailMedicalDocuments" AS reference ON reference."Id" = doublon."DuplicateOfId"
-- WHERE doublon."DuplicateOfId" IS NOT NULL
--   AND doublon."Ins" IS DISTINCT FROM reference."Ins";
--
-- `deja_rejetes_par_le_praticien` mesure ce que le défaut a coûté en travail
-- manuel : chacune de ces lignes est un praticien qui a dû retrouver le document
-- dans sa boîte et rejeter à la main un signal de doublon pointant sur le
-- dossier de quelqu'un d'autre.
-- =============================================================================
