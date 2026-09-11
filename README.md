# Mine de Ketchup — commandes détaillants

Application Streamlit + Supabase qui permet aux détaillants **déjà connus** de
Mine de Ketchup d'envoyer leurs commandes en ligne, **sans compte, sans mot de
passe et sans paiement**.

Le principe : le producteur enregistre un détaillant **une seule fois** dans le
tableau de bord ; ensuite, ce détaillant commande en **3 clics** :

1. il se choisit dans la liste déroulante,
2. il ajuste les quantités avec les gros boutons `+` / `−`,
3. il envoie.

Aucune coordonnée n'est retapée à chaque commande.

## Structure du projet

```
MineKetchup/
├── app.py                        # Page publique : commande en 3 clics
├── pages/
│   └── 1_Tableau_de_bord.py      # Admin : commandes + produits + détaillants
├── lib/
│   ├── supabase_client.py        # Connexion à Supabase (clé anon / service_role)
│   └── branding.py               # Palette, CSS et composants d'habillage partagés
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
   - la table **`retailers`** (les détaillants de la liste déroulante) ;
   - la vue **`retailers_public`** (id + nom du commerce seulement) ;
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
remplissez les 4 valeurs. **Aucun nouveau secret n'a été ajouté** par la version
« détaillants enregistrés » : la table `retailers` et la vue `retailers_public`
utilisent les mêmes clés. Ce fichier ne doit jamais être committé — `.gitignore`
l'exclut déjà.

## 3. Tester en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

- `http://localhost:8501` → page de commande (ce que voient les détaillants).
- `http://localhost:8501/Tableau_de_bord` → tableau de bord, protégé par
  `ADMIN_PASSWORD`.

## 4. Démarrer : saisir vos détaillants

C'est la seule étape manuelle avant que tout roule tout seul.

Tableau de bord → onglet **🏪 Détaillants** → **➕ Ajouter un détaillant** :
nom du commerce (obligatoire), contact, téléphone, courriel, notes internes.

Dès qu'un détaillant est dans la liste, il apparaît dans la liste déroulante de
la page de commande et peut commander en 3 clics. Pour retirer un détaillant de
la liste sans perdre son historique : bouton **Désactiver**.

> Les téléphones et courriels saisis ici ne sont **jamais** exposés à la page
> publique : celle-ci ne lit que la vue `retailers_public`, qui ne contient que
> l'id et le nom du commerce.

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

Une commande envoyée via le formulaire de secours (« mon commerce n'est pas dans
la liste ») est signalée par un avertissement : c'est le rappel d'ajouter ce
commerce dans l'onglet Détaillants.

## 7. Déployer

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
  - lire la vue `retailers_public` (id + nom du commerce) ;
  - **insérer** des commandes et des lignes de commande.
  Elle ne peut relire aucune commande, ni lire la table `retailers` complète.
- `ADMIN_PASSWORD` est une protection simple, suffisante pour un seul
  producteur. Pour plusieurs comptes admin, migrer vers Supabase Auth.

## Habillage visuel

Tout l'habillage est centralisé dans `lib/branding.py` (palette, CSS,
composants) et `.streamlit/config.toml` (thème Streamlit). Pour ajuster les
couleurs, il suffit de modifier le dictionnaire `BRAND` en haut de
`lib/branding.py` : les deux pages suivent.

Choix faits pour le mobile (les détaillants commanderont surtout au téléphone) :
cartes produits à grande cible tactile, boutons `+` / `−` de 48 px qui restent
côte à côte même sur petit écran, options facultatives repliées, et bouton
d'envoi qui rappelle ce qui manque tant que la commande est incomplète.

## Améliorations possibles

- Notification courriel au producteur à chaque nouvelle commande
  (webhook Supabase + Resend/SendGrid).
- Export CSV/Excel des commandes.
- Historique des commandes par détaillant dans le tableau de bord.
- Photos des produits (ajouter les URL dans l'onglet Produits).
