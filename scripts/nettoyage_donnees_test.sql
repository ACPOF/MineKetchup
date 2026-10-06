-- ============================================================
-- Nettoyage des données de test
--
-- À exécuter dans Supabase > SQL Editor, AVANT de remettre l'outil au client,
-- pour qu'aucune commande d'essai ne traîne dans sa comptabilité.
--
-- Les blocs sont numérotés et se lancent UN PAR UN : regardez le résultat de
-- l'étape 1 avant de supprimer quoi que ce soit. L'éditeur SQL affichera un
-- avertissement « destructive operations » — c'est normal, il se déclenche sur
-- le mot « delete » sans regarder ce qui est supprimé.
-- ============================================================


-- ------------------------------------------------------------
-- 1. REGARDER d'abord : qu'y a-t-il en base ?
-- ------------------------------------------------------------
select
    o.created_at::date            as recue_le,
    coalesce(r.business_name, o.retailer_name) as commerce,
    o.status                      as statut,
    count(i.id)                   as lignes,
    upper(split_part(o.id::text, '-', 1)) as numero
from orders o
left join retailers  r on r.id = o.retailer_id
left join order_items i on i.order_id = o.id
group by o.id, r.business_name, o.retailer_name, o.status, o.created_at
order by o.created_at;

select business_name, email, is_active, created_at::date
from retailers
order by business_name;


-- ------------------------------------------------------------
-- 2. SUPPRIMER TOUTES les commandes
--
-- C'est le cas normal avant une mise en service : tout ce qui existe est du
-- test. Les lignes de order_items partent d'elles-mêmes (suppression en
-- cascade), la ligne ci-dessous ne sert qu'à le rendre visible.
-- ------------------------------------------------------------
-- delete from order_items;
-- delete from orders;


-- ------------------------------------------------------------
-- 2 bis. OU supprimer seulement certaines commandes
--
-- Si de vraies commandes ont déjà été passées, remplacez les numéros ci-dessous
-- par ceux relevés à l'étape 1 (colonne « numero »), puis décommentez.
-- ------------------------------------------------------------
-- delete from orders
--  where upper(split_part(id::text, '-', 1)) in ('AB12CD34', 'EF56GH78');


-- ------------------------------------------------------------
-- 3. SUPPRIMER les détaillants de test
--
-- Nommés un par un volontairement : un filtre du genre « %test% » finirait un
-- jour par emporter un vrai commerce.
-- ------------------------------------------------------------
-- delete from retailers
--  where business_name in ('TEST — Atelier');


-- ------------------------------------------------------------
-- 4. VÉRIFIER que tout est propre
-- ------------------------------------------------------------
select
    (select count(*) from orders)       as commandes,
    (select count(*) from order_items)  as lignes_de_commande,
    (select count(*) from retailers)    as detaillants,
    (select count(*) from products)     as produits;
