# Revue complète du tableau de bord PEN-Plus (18 octobre 2026)

Demande : présenter le tableau de bord au directeur avec les données disponibles, sans mode
démo ni mention « ICPPA », et revoir chaque onglet, chaque chiffre, chaque visuel et son
utilité, couleurs comprises.

## Décisions générales

| Sujet | Avant | Décision |
|---|---|---|
| Mode démo | Bouton « Afficher avec des données de démonstration », jeu fictif dans `site/public/demo-data` | Supprimé : bouton, bandeau, code et données fictives. |
| Mentions « ICPPA » | Bandeau sur chaque écran, puces « Historique (ICPPA 2026) », légendes, sources de diapositives | Supprimées. Reste une seule mention neutre en pied de page : « Données déclarées par les pays, juin 2026 ; seront remplacées par les rapports trimestriels validés ». |
| Totaux régionaux de patients | « Suspendu · Q-REG-01 » à la place du chiffre | Publiés : somme des chiffres déclarés par les pays, avec le nombre de pays couverts (« 10 pays sur 31 »). Décision du programme, la requête Q-REG-01 est close. |
| Zimbabwe 4 590 | Suspendu (définition des cas à confirmer) | Reste hors du total régional (le chiffre de DT1 n'est pas plausible), affiché dans le tableau des pays avec la mention « à vérifier ». |
| Localisation « approximative » | Statistiques, légende, colonne et fiche distinguaient points exacts et approximatifs | Retiré de l'affichage : une formation = un point. L'information reste dans les données et dans l'export CSV. |
| Badges « Partiel · 48 % » | Orange sur presque chaque carte | Retirés. La couverture reste écrite (« 15 pays sur 31 ») et la valeur passe en ton atténué sous 80 % (règle 6 de CLAUDE.md). L'orange est réservé aux alertes. |
| Couleurs | Bleu marine + orange, beaucoup de nuances proches | Palette resserrée : bleu marine OMS (structure), bleu OMS #009ADE (accent de données : barres, points, sélection), orange #E8743B uniquement pour les alertes ; couleurs des affections du dossier de design (DT1 #016294, drépanocytose #C8102E, RAA #6B4FA0) pour les seuls graphiques par affection. |

## Onglet par onglet

### 1. Vue d'ensemble — « Où est PEN-Plus et quelle est son ampleur ? »

| Élément | Constat | Décision |
|---|---|---|
| Carte isométrique décorative | Joli mais n'apprend rien : ni frontières, ni formations | Remplacée par la vraie carte (frontières OMS), pays colorés par cycle HCT, une goutte lumineuse par formation. |
| 5 cartes chiffres (3 « Suspendu ») | Le directeur voyait « Suspendu » au lieu d'un chiffre | 5 chiffres réels : pays PEN-Plus, formations actives, patients (DT1, drépanocytose, RAA), agents de santé formés, pays en phase 4 ou 5. |
| Bande « Progrès vers les jalons » | 5 lignes « jalon non encore publié » : vide d'information | Retirée de la vue d'ensemble (reste dans le détail de chaque indicateur). |
| Listes des cohortes | Doublon de la carte, peu lisible | Remplacées par un tableau « Situation par pays » : cycle, phase, formations, patients, agents formés, avec barres discrètes. Ordre alphabétique, jamais un classement (règle 5). |

### 2. Détail d'un indicateur

| Élément | Constat | Décision |
|---|---|---|
| Liste des indicateurs | 18 entrées dont 12 sans aucune donnée | Indicateurs avec données d'abord ; les autres marqués « pas encore de données ». |
| Carte « Écart au jalon » | Toujours « non publié » | Remplacée par « Dernière mise à jour ». |
| 21 pastilles de pays sans valeur | Encombrant | Une ligne repliable. |
| Puces « Historique (ICPPA 2026) », références de diapositives | Bruit technique | Retirées de l'affichage. |
| Patients par affection | Absent | Nouveau graphique : patients par pays et par affection (DT1, drépanocytose, RAA), couleurs du dossier de design. |

### 3. Profil pays

| Élément | Constat | Décision |
|---|---|---|
| En-tête avec tuile isométrique | Décoratif | Vraie silhouette du pays (frontières OMS) avec ses formations. |
| 17 indicateurs, dont 15 « Non déclaré » | Le pays paraît vide | Les indicateurs renseignés en cartes chiffres ; les autres sur une seule ligne « pas encore de données ». |
| Requêtes de qualité | Technique pour un directeur | Repliées dans « Notes sur les données ». |

### 4. Phases de mise en œuvre

| Élément | Constat | Décision |
|---|---|---|
| Barres par phase | Correct | Gardé, couleurs alignées. |
| Absent : où en est chaque pays sur une carte | — | Nouvelle carte des phases (pays colorés du clair au foncé), placée après les chiffres clés. |
| Encadrés « divergence classeur / carte » | Alarmant | Note discrète dans le tableau. |

### 5. Qualité des données

| Élément | Constat | Décision |
|---|---|---|
| Écran très long, vocabulaire d'analyste | Utile à l'équipe, lourd pour un directeur | Gardé, resserré : chiffres clés, matrice de couverture, requêtes ; règles R01-R17 et provenance repliées. |

### 6. Formations sanitaires

| Élément | Constat | Décision |
|---|---|---|
| Distinction exact / approximatif | Brouille le message | Retirée de l'affichage. |
| Carte atlas | Bonne base | Gardée, harmonisée avec la nouvelle palette. |
