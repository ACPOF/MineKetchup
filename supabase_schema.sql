-- ============================================================
-- Mine de Ketchup — schéma Supabase de l'app de commandes
-- À exécuter dans Supabase : Dashboard > SQL Editor > New query
--
-- Ce script est IDEMPOTENT : vous pouvez le ré-exécuter sur une base
-- existante, il ajoute ce qui manque sans détruire vos commandes.
-- ============================================================

create extension if not exists "pgcrypto";

-- ------------------------------------------------------------
-- Table : retailers (les détaillants connus du producteur)
--
-- C'est LE raccourci du projet : le producteur saisit le détaillant
-- une seule fois ici (via le tableau de bord), et ensuite le détaillant
-- n'a plus qu'à se choisir dans une liste déroulante pour commander.
-- ------------------------------------------------------------
create table if not exists retailers (
    id uuid primary key default gen_random_uuid(),
    business_name text not null,      -- nom du commerce, affiché dans la liste
    contact_name text,                -- personne contact
    phone text,
    email text,
    notes text,                       -- notes internes (jamais montrées au détaillant)
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create unique index if not exists idx_retailers_business_name
    on retailers (lower(business_name));
create index if not exists idx_retailers_active
    on retailers (is_active, business_name);

-- ------------------------------------------------------------
-- Table : products (catalogue géré par le producteur)
-- ------------------------------------------------------------
create table if not exists products (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    description text,
    category text,
    unit text not null default 'unité',   -- format de vente : 'bouteille 350 ml', 'caisse de 12'...
    price numeric(10,2),                  -- optionnel, informatif (aucun paiement dans l'app)
    is_active boolean not null default true,
    sort_order integer not null default 0,
    created_at timestamptz not null default now()
);

-- Ajout (migration) de la colonne image pour les fiches produits
alter table products add column if not exists image_url text;

create unique index if not exists idx_products_name on products (lower(name));

-- ------------------------------------------------------------
-- Table : orders (une commande = un détaillant, une soumission)
-- ------------------------------------------------------------
create table if not exists orders (
    id uuid primary key default gen_random_uuid(),
    retailer_name text,                -- fallback texte : « mon commerce n'est pas dans la liste »
    contact_name text,
    phone text,
    email text,
    requested_date date,               -- date de livraison/collecte souhaitée (optionnelle)
    notes text,
    status text not null default 'nouvelle'
        check (status in ('nouvelle', 'en préparation', 'prête', 'complétée', 'annulée')),
    created_at timestamptz not null default now()
);

-- Migration : référence vers le détaillant enregistré + champs texte devenus optionnels
alter table orders add column if not exists retailer_id uuid
    references retailers(id) on delete set null;
alter table orders alter column retailer_name drop not null;

-- Une commande doit toujours identifier son auteur, d'une façon ou de l'autre.
alter table orders drop constraint if exists orders_retailer_present;
alter table orders add constraint orders_retailer_present
    check (retailer_id is not null or retailer_name is not null);

create index if not exists idx_orders_retailer_id on orders (retailer_id);

-- ------------------------------------------------------------
-- Table : order_items (lignes de commande)
-- ------------------------------------------------------------
create table if not exists order_items (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references orders(id) on delete cascade,
    product_id uuid references products(id) on delete set null,
    product_name text not null,   -- copie du nom au moment de la commande (historique)
    unit text not null,           -- copie de l'unité au moment de la commande
    quantity numeric(10,2) not null check (quantity > 0),
    price numeric(10,2),          -- copie du prix au moment de la commande (optionnel)
    created_at timestamptz not null default now()
);

create index if not exists idx_order_items_order_id on order_items (order_id);
create index if not exists idx_orders_status on orders (status);
create index if not exists idx_orders_created_at on orders (created_at desc);

-- ============================================================
-- Row Level Security
-- ============================================================
-- Principe inchangé :
--   - la page de commande (publique, sans mot de passe) utilise la clé anon :
--     elle peut LIRE les produits actifs, LIRE la liste des détaillants
--     (nom du commerce seulement, via une vue) et INSÉRER des commandes ;
--   - le tableau de bord utilise la clé service_role (accès complet), gardée
--     dans les secrets Streamlit et jamais envoyée au navigateur.
-- ============================================================

alter table products enable row level security;
alter table orders enable row level security;
alter table order_items enable row level security;
alter table retailers enable row level security;

drop policy if exists "public read active products" on products;
create policy "public read active products"
    on products for select
    using (is_active = true);

drop policy if exists "public insert orders" on orders;
create policy "public insert orders"
    on orders for insert
    with check (true);

drop policy if exists "public insert order_items" on order_items;
create policy "public insert order_items"
    on order_items for insert
    with check (true);

-- ATTENTION : aucune policy de lecture sur `retailers`. La clé anon ne peut
-- donc PAS lire les téléphones/courriels de vos détaillants. La page publique
-- lit uniquement la vue ci-dessous, qui n'expose que l'id et le nom du commerce.
create or replace view retailers_public as
    select id, business_name
    from retailers
    where is_active = true;

-- La vue s'exécute avec les droits de son propriétaire (postgres), donc elle
-- « traverse » le RLS de retailers — c'est voulu, et elle ne contient que
-- deux colonnes non sensibles.
alter view retailers_public set (security_invoker = off);
grant select on retailers_public to anon, authenticated;

-- Note : aucune policy SELECT/UPDATE/DELETE publique sur orders/order_items.

-- ============================================================
-- Catalogue de départ — vrais produits Mine de Ketchup
-- ------------------------------------------------------------
-- Les 3 produits d'exemple de la première version sont retirés.
-- Les PRIX sont volontairement laissés vides : les prix trouvés en ligne
-- sont des prix de DÉTAIL au consommateur, pas vos prix de gros.
-- Saisissez-les dans le tableau de bord > Gestion des produits.
-- (Pour référence, prix de détail public relevés chez des revendeurs :
--  ketchup 350 ml ≈ 7,25 $ ; salsa 500 ml ≈ 8,50 $.)
-- ============================================================

delete from products
 where lower(name) in (
    'confiture de fraises',
    'sauce tomate maison',
    'pain aux noix'
 );

insert into products (name, description, category, unit, price, sort_order) values
    ('Ketchup classique',
     'Riche et savoureux, le classique incontournable. Sans agents de conservation.',
     'Ketchups', 'bouteille 350 ml', null, 10),
    ('Ketchup épicé',
     'Le même bon goût, juste assez relevé pour réveiller le palais.',
     'Ketchups', 'bouteille 350 ml', null, 20),
    ('Ketchup fumé au rhum nordique',
     'Fumé, audacieux, au rhum nordique de la Distillerie Mitis. Le favori du BBQ.',
     'Ketchups', 'bouteille 350 ml', null, 30),
    ('Ketchup pour fruits de mer',
     'Ketchup pensé pour accompagner poissons et fruits de mer. (Description à confirmer.)',
     'Ketchups', 'bouteille 350 ml', null, 40),
    ('Salsa douce',
     'Bien tomatée et tout en douceur — parfaite pour toute la famille.',
     'Salsas', 'pot 500 ml', null, 50),
    ('Salsa moyenne',
     'Un cran plus relevée, avec du jalapeño.',
     'Salsas', 'pot 500 ml', null, 60),
    ('Salsa épicée',
     'Du piment de Cayenne pour un beau coup de fouet.',
     'Salsas', 'pot 500 ml', null, 70)
on conflict do nothing;
