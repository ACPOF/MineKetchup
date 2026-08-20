# App de commandes — détaillants → producteur

Petite application Streamlit qui permet à vos détaillants de vous envoyer
leurs commandes en ligne, sans identification et sans paiement. Vous
consultez et gérez les commandes reçues dans un tableau de bord protégé
par mot de passe.

## Structure du projet

```
commande-app/
├── app.py                        # Page publique : formulaire de commande
├── pages/
│   └── 1_Tableau_de_bord.py      # Page admin (protégée par mot de passe)
├── lib/
│   └── supabase_client.py        # Connexion à Supabase
├── supabase_schema.sql           # Script SQL à exécuter dans Supabase
├── requirements.txt
├── .streamlit/
│   └── secrets.toml.example      # Modèle des secrets à configurer
└── README.md
```

## 1. Configurer Supabase

1. Dans votre projet Supabase (ou un nouveau projet), allez dans
   **SQL Editor** → **New query**.
2. Collez le contenu de `supabase_schema.sql` et exécutez-le. Cela crée
   les tables `products`, `orders`, `order_items`, active la sécurité au
   niveau des lignes (RLS) et insère 3 produits d'exemple.
3. Allez dans **Project Settings → API** et notez :
   - **Project URL** → `SUPABASE_URL`
   - **anon / public key** → `SUPABASE_ANON_KEY`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ gardez-la secrète,
     elle donne un accès complet à la base de données)

## 2. Configurer les secrets de l'app

Copiez `.streamlit/secrets.toml.example` vers `.streamlit/secrets.toml`
et remplissez les 4 valeurs (URL, anon key, service_role key, mot de passe
admin de votre choix). Ce fichier ne doit jamais être partagé publiquement
ni ajouté à un dépôt Git public — `.gitignore` l'exclut déjà.

## 3. Tester en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

- La page principale (`http://localhost:8501`) est le formulaire de
  commande, destiné aux détaillants.
- Le tableau de bord admin est accessible via le menu de gauche
  ("Tableau de bord") ou `http://localhost:8501/Tableau_de_bord`.

## 4. Gérer le catalogue de produits

Le plus simple est d'éditer directement la table `products` dans
Supabase (**Table Editor**) :
- `name`, `description`, `category`, `unit`, `price` : ce qui s'affiche
  aux détaillants.
- `is_active` : mettre à `false` pour retirer un produit sans l'effacer.
- `sort_order` : contrôle l'ordre d'affichage (plus petit = plus haut).

Si vous préférez gérer le catalogue directement depuis l'app plus tard
(sans passer par Supabase), on peut ajouter une page admin pour ça —
dites-le-moi.

## 5. Déployer

Option recommandée, gratuite et simple : **Streamlit Community Cloud**
(puisque vous utilisez déjà Streamlit) :

1. Mettez ce dossier dans un dépôt GitHub (privé ou public — mais sans
   `secrets.toml`, seulement `secrets.toml.example`).
2. Sur [share.streamlit.io](https://share.streamlit.io), créez une nouvelle
   app à partir de ce dépôt, fichier principal `app.py`.
3. Dans les **Settings → Secrets** de l'app déployée, collez le contenu
   de votre `secrets.toml` rempli.
4. L'app publique sera accessible à une URL du type
   `https://votre-app.streamlit.app` — c'est le lien à envoyer aux
   détaillants. Le tableau de bord est protégé par le mot de passe même
   si le lien est connu.

## Sécurité — points importants

- La clé **service_role** (accès total à la base) n'est utilisée que côté
  serveur (dans le code Python du tableau de bord), jamais envoyée au
  navigateur — c'est sûr tant qu'elle reste dans les secrets Streamlit.
- La clé **anon**, utilisée par la page de commande publique, est limitée
  par les policies RLS définies dans `supabase_schema.sql` : elle ne peut
  que lire les produits actifs et insérer de nouvelles commandes — jamais
  lire ou modifier les commandes existantes.
- Le mot de passe admin (`ADMIN_PASSWORD`) est une protection simple,
  suffisante pour un usage à petite échelle avec un seul producteur. Pour
  plusieurs utilisateurs admin ou plus de sécurité, on pourrait migrer
  vers Supabase Auth plus tard.

## Prochaines améliorations possibles

- Notification par courriel automatique au producteur à chaque nouvelle
  commande (via un webhook Supabase + service comme Resend/SendGrid).
- Export CSV/Excel des commandes depuis le tableau de bord.
- Gestion du catalogue directement dans l'app (sans passer par Supabase).
- Historique des commandes par détaillant (nécessiterait un système de
  compte, actuellement volontairement omis pour rester simple).
