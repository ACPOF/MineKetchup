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
-- C'est LE raccourci du projet : le producteur saisit le détaillant une
-- seule fois ici (via le tableau de bord) et lui envoie son lien de
-- commande personnel ; ensuite, ouvrir ce lien suffit à l'identifier.
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
-- Lien de commande personnel
--
-- Chaque détaillant a un code court et unique. Son lien de commande est
-- https://votre-app.streamlit.app/?c=XXXXXXXX : la page l'identifie toute
-- seule, donc AUCUNE liste de détaillants n'est jamais affichée ni envoyée
-- au navigateur. La liste de clients du producteur reste confidentielle.
--
-- Alphabet sans caractères ambigus (pas de O/0, I/1) : le code reste
-- dictable au téléphone si besoin. 8 caractères sur 32 symboles, soit plus
-- de 1000 milliards de combinaisons — non devinable.
-- ------------------------------------------------------------
create or replace function gen_retailer_code() returns text
language plpgsql
as $$
declare
    alphabet text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    code text;
begin
    loop
        code := '';
        for i in 1..8 loop
            code := code || substr(alphabet, 1 + floor(random() * length(alphabet))::int, 1);
        end loop;
        exit when not exists (select 1 from retailers where access_code = code);
    end loop;
    return code;
end
$$;

alter table retailers add column if not exists access_code text;
update retailers set access_code = gen_retailer_code() where access_code is null;
alter table retailers alter column access_code set default gen_retailer_code();
alter table retailers alter column access_code set not null;

create unique index if not exists idx_retailers_access_code
    on retailers (access_code);

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
-- Date du dernier changement de statut
--
-- Le rapport à la comptable raisonne par SEMAINE DE TRAVAIL, pas par date de
-- commande : ce qui se facture, c'est ce qui a été complété cette semaine,
-- même si la commande date d'avant. Sans cette colonne, l'information
-- n'existe nulle part — `created_at` ne dit que la date de réception.
-- ------------------------------------------------------------
alter table orders add column if not exists status_changed_at timestamptz;
update orders set status_changed_at = created_at where status_changed_at is null;
alter table orders alter column status_changed_at set default now();
alter table orders alter column status_changed_at set not null;

create index if not exists idx_orders_status_changed_at
    on orders (status_changed_at desc);

create or replace function touch_order_status() returns trigger
language plpgsql
as $$
begin
    if new.status is distinct from old.status then
        new.status_changed_at := now();
    end if;
    return new;
end
$$;

drop trigger if exists trg_orders_status_changed on orders;
create trigger trg_orders_status_changed
    before update on orders
    for each row execute function touch_order_status();

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
--     elle peut LIRE les produits actifs, RÉSOUDRE un code de détaillant
--     (un seul à la fois, via la fonction retailer_by_code) et INSÉRER des
--     commandes — jamais lister les détaillants ;
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
-- donc ni lire les coordonnées de vos détaillants, ni ÉNUMÉRER la liste.
--
-- La version précédente exposait une vue `retailers_public` pour alimenter une
-- liste déroulante : elle est retirée ici, car elle laissait n'importe quel
-- visiteur lire toute la liste de clients du producteur.
drop view if exists retailers_public;

-- À la place, une seule fonction, qui répond uniquement à la question
-- « à quel commerce correspond CE code ? ». Elle ne peut rien lister : sans
-- le bon code, elle ne renvoie rien.
--
-- Elle renvoie le nom du contact et le courriel, nécessaires pour envoyer au
-- détaillant la confirmation de SA commande. Ce sont ses propres coordonnées,
-- remises à qui présente son propre lien, et elles ne quittent jamais le
-- serveur Streamlit. Le téléphone, inutile ici, n'est pas exposé.
--
-- drop avant create : on ne peut pas changer le type de retour d'une fonction
-- avec un simple « create or replace ».
drop function if exists retailer_by_code(text);
create function retailer_by_code(p_code text)
returns table (id uuid, business_name text, contact_name text, email text)
language sql
security definer
set search_path = public
stable
as $$
    select r.id, r.business_name, r.contact_name, r.email
    from retailers r
    where r.is_active = true
      and r.access_code = upper(trim(p_code))
    limit 1;
$$;

revoke all on function retailer_by_code(text) from public;
grant execute on function retailer_by_code(text) to anon, authenticated;

-- Note : aucune policy SELECT/UPDATE/DELETE publique sur orders/order_items.

-- ============================================================
-- Droits d'accès aux tables (GRANT)
-- ------------------------------------------------------------
-- RLS filtre les LIGNES ; encore faut-il que le rôle ait le droit
-- d'interroger la TABLE. Les anciens projets Supabase accordaient ces droits
-- d'office à anon / authenticated / service_role ; les projets récents ne le
-- font plus pour les tables créées en SQL. Sans ces lignes, la page de
-- commande échoue avec « permission denied for table products » (42501).
--
-- On les donne donc explicitement, au plus juste : la clé anon reçoit
-- exactement ce que les policies ci-dessus autorisent, rien de plus.
-- ============================================================

revoke all on retailers, products, orders, order_items from anon, authenticated;

grant select on products to anon;
grant insert on orders, order_items to anon;

-- Tableau de bord et rapport hebdomadaire (clé service_role, côté serveur).
grant all on retailers, products, orders, order_items to service_role;

-- ------------------------------------------------------------
-- Photos des produits (Supabase Storage)
--
-- Compartiment public en LECTURE : la page de commande affiche les photos par
-- leur adresse. Seul le tableau de bord (clé service_role) y écrit. Le
-- tableau de bord le crée aussi lui-même au premier envoi s'il manque.
-- ------------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('produits', 'produits', true)
on conflict (id) do update set public = true;

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
