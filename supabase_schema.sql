-- ============================================================
-- Schéma Supabase pour l'app de commandes (détaillants -> producteur)
-- À exécuter dans Supabase : Dashboard > SQL Editor > New query
-- ============================================================

-- Extension pour générer des UUID
create extension if not exists "pgcrypto";

-- ------------------------------------------------------------
-- Table : products (catalogue géré par le producteur)
-- ------------------------------------------------------------
create table if not exists products (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    description text,
    category text,
    unit text not null default 'unité',   -- ex: 'caisse de 12', 'kg', 'unité'
    price numeric(10,2),                   -- optionnel, purement informatif (pas de paiement)
    is_active boolean not null default true,
    sort_order integer not null default 0,
    created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- Table : orders (une commande = un détaillant, une soumission)
-- ------------------------------------------------------------
create table if not exists orders (
    id uuid primary key default gen_random_uuid(),
    retailer_name text not null,       -- nom du commerce détaillant
    contact_name text,                 -- nom de la personne contact
    phone text,
    email text,
    requested_date date,               -- date de livraison/collecte souhaitée
    notes text,                        -- notes ou produits hors-catalogue
    status text not null default 'nouvelle'
        check (status in ('nouvelle', 'en préparation', 'prête', 'complétée', 'annulée')),
    created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- Table : order_items (lignes de commande, liées à orders)
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

create index if not exists idx_order_items_order_id on order_items(order_id);
create index if not exists idx_orders_status on orders(status);
create index if not exists idx_orders_created_at on orders(created_at desc);

-- ============================================================
-- Row Level Security
-- ============================================================
-- Principe :
--   - La page "commande" (publique, sans identification) utilise la clé
--     anon et ne peut que LIRE les produits actifs et INSÉRER des commandes.
--   - La page "tableau de bord" (admin, protégée par mot de passe dans
--     l'app Streamlit) utilise la clé service_role (accès complet), gardée
--     uniquement dans les secrets du serveur Streamlit — jamais exposée au
--     navigateur du détaillant.
-- ============================================================

alter table products enable row level security;
alter table orders enable row level security;
alter table order_items enable row level security;

-- Lecture publique des produits actifs uniquement
create policy "public read active products"
    on products for select
    using (is_active = true);

-- Insertion publique de commandes (aucune lecture publique)
create policy "public insert orders"
    on orders for insert
    with check (true);

create policy "public insert order_items"
    on order_items for insert
    with check (true);

-- Note : aucune policy SELECT/UPDATE/DELETE publique sur orders/order_items.
-- Le tableau de bord admin utilise la clé service_role, qui contourne RLS.

-- ============================================================
-- Exemple de produits de départ (à adapter/effacer)
-- ============================================================
insert into products (name, description, category, unit, price, sort_order) values
    ('Confiture de fraises', 'Pot de 250 ml, sans agents de conservation', 'Confitures', 'unité', 6.50, 1),
    ('Sauce tomate maison', 'Bocal de 500 ml', 'Sauces', 'unité', 7.00, 2),
    ('Pain aux noix', 'Miche de 500 g', 'Boulangerie', 'unité', 5.50, 3)
on conflict do nothing;
