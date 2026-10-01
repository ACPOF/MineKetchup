# Mine de Ketchup — commandes détaillants

Application Streamlit + Supabase qui permet aux détaillants **déjà connus** de
Mine de Ketchup d'envoyer leurs commandes en ligne, **sans compte, sans mot de
passe et sans paiement**.

Le principe : le producteur enregistre un détaillant **une seule fois** dans le
tableau de bord, puis lui envoie son **lien de commande personnel**
(`.../?c=XXXXXXXX`). Ensuite, ce détaillant commande en **2 clics** :

1. il ouvre son lien — la page sait déjà quel commerce commande,
2. il ajuste les quantités avec les gros boutons `+` / `−`,
3. il envoie.

Aucune coordonnée n'est retapée à chaque commande.

> **Pourquoi un lien personnel plutôt qu'une liste déroulante ?** Une liste
> déroulante devrait charger tous les noms de commerces dans le navigateur de
> chaque visiteur : la liste de clients de Mine de Ketchup serait lisible par
> n'importe qui. Avec le lien personnel, la page publique ne peut résoudre
> qu'un seul code à la fois et n'affiche jamais de liste.

## Structure du projet

```
MineKetchup/
├── app.py                        # Page publique : commande en 2 clics
├── pages/
│   └── 1_Tableau_de_bord.py      # Admin : commandes + produits + détaillants
├── lib/
│   ├── supabase_client.py        # Connexion à Supabase (clé anon / service_role)
│   ├── branding.py               # Logo, palette, CSS et composants partagés
│   ├── settings.py               # Config : env → st.secrets → secrets.toml
│   ├── mailer.py                 # Envoi SMTP (jamais bloquant)
│   ├── emails.py                 # Gabarits des trois courriels
│   └── format.py                 # Formatage des prix (sans Streamlit)
├── scripts/
│   └── rapport_hebdo.py          # Rapport des commandes pour la comptable
├── .github/workflows/
│   └── rapport-hebdomadaire.yml  # Déclenche le rapport chaque lundi
├── assets/                       # (optionnel) logo officiel — voir assets/README.md
├── supabase_schema.sql           # Script SQL à exécuter dans Supabase (idempotent)
├── requirements.txt
├── .streamlit/
│   ├── config.toml               # Thème sombre Mine de Ketchup
│   └── secrets.toml.example      # Modèle des secrets à configurer
└── README.md
```

## 1. Configurer Supabase

1. Dans votre projet Supabase : **SQL Editor** → **New query**.
2. Collez le contenu de `supabase_schema.sql` et exécutez-le.
   Le script est **idempotent** : on peut le relancer sur une base existante
   sans perdre les commandes déjà reçues. Il crée / met à jour :
   - la table **`retailers`**, avec un **code d'accès unique** par détaillant ;
   - la fonction **`retailer_by_code`**, seule porte d'entrée publique : elle
     traduit un code en nom de commerce, un à la fois, et ne peut rien lister
     (l'ancienne vue `retailers_public` est supprimée) ;
   - la colonne **`orders.retailer_id`** et rend `orders.retailer_name`
     optionnel (il ne sert plus que de secours) ;
   - la colonne **`products.image_url`** ;
   - les policies RLS ;
   - le catalogue des 7 vrais produits (les 3 produits d'exemple sont retirés).
3. **Project Settings → API**, notez :
   - **Project URL** → `SUPABASE_URL`
   - **anon / public key** → `SUPABASE_ANON_KEY`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ secrète)

## 2. Configurer les secrets

Copiez `.streamlit/secrets.toml.example` vers `.streamlit/secrets.toml` et
remplissez les valeurs. Ce fichier ne doit jamais être committé — `.gitignore`
l'exclut déjà.

Un secret s'ajoute aux 4 existants :

| Secret | Obligatoire | Rôle |
|---|---|---|
| `SUPABASE_URL` | oui | projet Supabase |
| `SUPABASE_ANON_KEY` | oui | page de commande (limitée par RLS) |
| `SUPABASE_SERVICE_ROLE_KEY` | oui | tableau de bord uniquement |
| `ADMIN_PASSWORD` | oui | accès au tableau de bord |
| `APP_URL` | recommandé | adresse publique de l'app, pour composer les liens de commande personnels affichés dans le tableau de bord |
| `SMTP_*` | optionnel | envoi des courriels automatiques — voir la section 7 |
| `ORDER_NOTIFY_EMAIL` | optionnel | qui est alerté à chaque nouvelle commande |
| `ACCOUNTANT_EMAIL` | optionnel | destinataire du rapport hebdomadaire (secret GitHub, pas Streamlit) |

Sans `APP_URL`, tout fonctionne, mais le tableau de bord n'affiche que la partie
`?c=XXXXXXXX` du lien, à coller derrière votre adresse.

## 3. Tester en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

- `http://localhost:8501` → page de commande (ce que voient les détaillants).
- `http://localhost:8501/Tableau_de_bord` → tableau de bord, protégé par
  `ADMIN_PASSWORD`.

Le tableau de bord n'apparaît **pas** dans un menu : le menu latéral de
Streamlit est masqué (`showSidebarNavigation = false` dans
`.streamlit/config.toml`) pour ne pas en annoncer l'existence aux détaillants.
Un lien « Gestion », volontairement effacé, est posé tout en bas de la page de
commande. Sinon, on y accède en tapant l'adresse, à mettre en favori :

```
https://minedeketchup.streamlit.app/Tableau_de_bord
```

Ce n'est pas ce qui protège la page — c'est `ADMIN_PASSWORD` qui la protège —
mais ça évite qu'un détaillant tombe dessus par curiosité. Depuis le tableau de
bord, un lien « Page de commande » ramène côté public.

## 4. Démarrer : saisir vos détaillants et envoyer leurs liens

C'est la seule étape manuelle avant que tout roule tout seul.

1. Tableau de bord → onglet **🏪 Détaillants** → **➕ Ajouter un détaillant** :
   nom du commerce (obligatoire), contact, téléphone, courriel, notes internes.
2. Sa carte affiche aussitôt son **lien de commande personnel**. Copiez-le et
   envoyez-le-lui une fois par courriel — il n'a qu'à le mettre en favori.

Boutons utiles :

- **Désactiver** : le détaillant ne peut plus commander (son lien cesse de
  fonctionner), sans rien perdre de son historique.
- **Modifier → 🔗 Régénérer le lien** : crée un nouveau code et rend l'ancien
  inutilisable, si un lien a circulé par erreur. Comptez moins d'une minute
  pour que l'ancien lien cesse de fonctionner (durée du cache).

> Les téléphones et courriels saisis ici ne sont **jamais** exposés à la page
> publique, et la liste des détaillants non plus : la page publique ne peut
> qu'appeler `retailer_by_code`, qui répond pour un code à la fois.

### Un détaillant sans son lien

Il peut quand même commander : la page lui propose d'indiquer son commerce et
son nom à la main. Ces commandes sont signalées dans l'onglet Commandes par un
avertissement, avec un bouton **➕ Enregistrer ce commerce** : un clic crée le
détaillant à partir des coordonnées de la commande, lui rattache les commandes
déjà reçues sous ce nom, et lui attribue son lien personnel (à récupérer dans
l'onglet Détaillants). Ça reste l'exception, pas le chemin normal.

## 5. Gérer le catalogue

Tableau de bord → onglet **🧂 Produits** :

- **➕ Ajouter un produit** : nom, description, catégorie, format/unité, prix,
  URL d'image.
- **Modifier** : ouvre le formulaire d'édition d'un produit.
- **Désactiver / Activer** : retire ou remet un produit dans la page de
  commande, sans toucher à l'historique des commandes.
- **⬆️ / ⬇️** : change l'ordre d'affichage chez les détaillants.
- Un prix à `0` signifie « aucun prix affiché » (la carte produit montre alors
  seulement le format).

## 6. Suivre les commandes

Tableau de bord → onglet **📋 Commandes** : compteurs par statut, filtre, puis
une carte dépliable par commande (coordonnées du détaillant, articles, date
souhaitée, notes) avec changement de statut
(`nouvelle` → `en préparation` → `prête` → `complétée` / `annulée`).

Une commande envoyée sans lien personnel est signalée par un avertissement :
c'est le rappel d'ajouter ce commerce dans l'onglet Détaillants (ou de lui
renvoyer son lien).

## 7. Courriels automatiques

Trois courriels, tous optionnels : **sans configuration SMTP, l'app fonctionne
exactement comme avant et n'envoie rien**.

| Courriel | Quand | Pour qui |
|---|---|---|
| Nouvelle commande | à chaque commande reçue | `ORDER_NOTIFY_EMAIL` |
| Confirmation | à chaque commande, si le commerce a un courriel connu | le détaillant |
| Rapport des commandes | chaque lundi matin | `ACCOUNTANT_EMAIL` |

### Configurer l'envoi

Ajoutez les valeurs SMTP aux secrets (voir `.streamlit/secrets.toml.example`).
Avec Gmail ou Microsoft 365, `SMTP_PASSWORD` doit être un **mot de passe
d'application**, pas le mot de passe du compte.

Le code refuse d'envoyer vos identifiants en clair : si le serveur n'accepte
pas STARTTLS (port 587) ou le TLS direct (port 465), l'envoi échoue plutôt que
de les exposer.

> **Un courriel qui ne part pas ne fait jamais perdre une commande.** L'envoi
> a lieu après l'enregistrement en base, il est encapsulé, et le détaillant
> voit sa confirmation même si le serveur de courriel est en panne. Les échecs
> sont écrits dans les journaux de l'app (Streamlit Cloud → *Manage app*).

### Le rapport hebdomadaire

Streamlit Cloud endort l'app quand personne ne l'utilise : elle ne peut donc
pas se réveiller seule pour envoyer un rapport. C'est **GitHub Actions** qui
déclenche `scripts/rapport_hebdo.py`, chaque lundi à 11 h UTC (7 h l'été, 6 h
l'hiver, heure du Québec).

Recopiez ces secrets dans **Settings → Secrets and variables → Actions** du
dépôt : `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SMTP_HOST`, `SMTP_PORT`,
`SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `ACCOUNTANT_EMAIL`.

Le rapport est construit pour la **facturation**, en deux sections.

**1. Commandes complétées — à facturer.** Le détail, commerce par commerce et
commande par commande : articles, quantités, prix, sous-totaux. Un bandeau en
tête donne le **montant total à facturer**, qui est aussi dans l'objet du
courriel.

**2. Autres commandes ayant évolué.** Un résumé d'une ligne par commande :
date du changement, commerce, numéro, date de commande, statut et montant.
Pour information — rien à facturer là.

> **La période se lit sur la date de changement de statut, pas sur la date de
> commande.** Une commande passée il y a trois semaines et livrée lundi se
> facture *cette* semaine-ci. C'est la colonne `orders.status_changed_at`,
> tenue à jour par un déclencheur Postgres ; sans elle, le script se rabat sur
> la date de commande et le signale dans le courriel.

Les commandes annulées apparaissent dans la section 2, signalées comme telles,
plutôt que d'être passées sous silence : savoir qu'une commande a été annulée
dans la semaine évite de la facturer par erreur.

Un **CSV** est joint : une ligne par article, les deux sections réunies et
distinguées par une colonne `Section`, séparateur `;`, BOM UTF-8 pour qu'Excel
en français ne massacre pas les accents.

**Une semaine sans mouvement déclenche quand même un courriel**, qui le dit
explicitement. C'est volontaire : son arrivée confirme que la prise de commande
et l'envoi fonctionnent, là où un silence ne distinguerait pas « aucune
commande » de « le rapport est cassé ». L'option `--taire-si-vide` rétablit le
silence.

Lancement à la main, depuis l'onglet **Actions** du dépôt (bouton *Run
workflow*, avec dates optionnelles) ou en local :

```bash
python scripts/rapport_hebdo.py                       # semaine précédente
python scripts/rapport_hebdo.py --jours 30
python scripts/rapport_hebdo.py --debut 2026-09-01 --fin 2026-09-30
python scripts/rapport_hebdo.py --essai               # affiche sans envoyer
```

## 8. Déployer

**Streamlit Community Cloud** :

1. Poussez ce dossier sur GitHub (sans `secrets.toml`).
2. Sur [share.streamlit.io](https://share.streamlit.io), créez l'app avec
   `app.py` comme fichier principal.
3. **Settings → Secrets** : collez le contenu de votre `secrets.toml`.
4. L'URL publique est le lien à envoyer aux détaillants. Le tableau de bord
   reste protégé par mot de passe même si le lien est connu.

## Sécurité

- La clé **service_role** (accès total) n'est utilisée que par le tableau de
  bord, côté serveur, après saisie de `ADMIN_PASSWORD`. Streamlit exécute tout
  le Python côté serveur : elle n'atteint jamais le navigateur.
- La clé **anon**, utilisée par la page publique, est limitée par RLS. Elle peut
  uniquement :
  - lire les produits **actifs** ;
  - appeler `retailer_by_code` avec **un** code, qui renvoie au plus un
    commerce (id, nom, contact et courriel — ses propres coordonnées, remises
    à qui présente son propre lien, et nécessaires pour lui confirmer sa
    commande ; elles ne quittent jamais le serveur Streamlit). Elle ne peut ni
    lire la table `retailers`, ni l'énumérer, et n'expose pas le téléphone. Un code fait 8 caractères sur un alphabet de 32, soit plus de
    1000 milliards de combinaisons : non devinable ;
  - **insérer** des commandes et des lignes de commande — sans jamais les
    relire. Les écritures utilisent `returning="minimal"` et un identifiant de
    commande généré côté app : PostgREST ne renvoie donc pas la ligne insérée,
    ce qu'il refuserait de toute façon faute de policy `SELECT` (erreur
    `42501 new row violates row-level security policy`).
  Elle ne peut relire aucune commande, ni lire la table `retailers` complète.
- `ADMIN_PASSWORD` est une protection simple, suffisante pour un seul
  producteur. Pour plusieurs comptes admin, migrer vers Supabase Auth.

## Habillage visuel

Tout l'habillage est centralisé dans `lib/branding.py` (logo, palette, CSS,
composants) et `.streamlit/config.toml` (thème Streamlit). Pour ajuster les
couleurs, il suffit de modifier le dictionnaire `BRAND` en haut de
`lib/branding.py` : les deux pages suivent.

### Le logo

Les deux pages affichent le lettrage de la marque — « MINE », les pics croisés,
« DE KETCHUP » — reconstruit en texte et en SVG plutôt qu'en image : il reste
net à toutes les tailles et prend la couleur crème du thème sombre, là où le
fichier officiel (noir sur blanc) formerait un rectangle blanc.

Pour utiliser le fichier officiel à la place, déposez-le dans `assets/` sous un
nom commençant par `logo` (`logo.png`, `logo.svg`…). Il est repris
automatiquement, et inversé pour ressortir sur le fond sombre ; un fichier déjà
clair doit s'appeler `logo-blanc.png`. Détails dans `assets/README.md`.

Choix faits pour le mobile (les détaillants commanderont surtout au téléphone) :
cartes produits à grande cible tactile, boutons `+` / `−` de 48 px qui restent
côte à côte même sur petit écran, options facultatives repliées, bandeau
« Commande pour <commerce> » dès l'ouverture du lien, et bouton d'envoi qui
rappelle ce qui manque tant que la commande est incomplète.

## Améliorations possibles

- Export CSV/Excel des commandes depuis le tableau de bord (le rapport
  hebdomadaire en joint déjà un, par courriel).
- Historique des commandes par détaillant dans le tableau de bord.
- Envoi automatique du lien personnel par courriel à l'ajout d'un détaillant.
- Photos des produits (ajouter les URL dans l'onglet Produits).
