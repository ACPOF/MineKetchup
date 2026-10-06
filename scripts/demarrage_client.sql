-- ============================================================
-- Démarrage : prix, détaillants, et liens à envoyer
--
-- Deux saisies font tout le travail de mise en service. Les faire ici plutôt
-- qu'une par une dans le tableau de bord est bien plus rapide quand il y a
-- une dizaine de détaillants à entrer.
--
-- Supabase > SQL Editor. Les blocs se lancent un par un.
-- Tout reste faisable à la main dans le tableau de bord — ce fichier n'est
-- qu'un raccourci pour le jour de la mise en route.
-- ============================================================


-- ------------------------------------------------------------
-- 1. LES PRIX DE GROS
--
-- Remplacez les montants par les vrais, puis lancez. Un produit laissé à null
-- s'affiche sans prix aux détaillants et ne compte pas dans les totaux du
-- rapport comptable.
-- ------------------------------------------------------------
update products set price = 5.50 where name = 'Ketchup classique';
update products set price = 5.50 where name = 'Ketchup épicé';
update products set price = 6.25 where name = 'Ketchup fumé au rhum nordique';
update products set price = 6.25 where name = 'Ketchup pour fruits de mer';
update products set price = 7.00 where name = 'Salsa douce';
update products set price = 7.00 where name = 'Salsa moyenne';
update products set price = 7.00 where name = 'Salsa épicée';

-- Vérifier : aucune ligne ne doit rester sans prix.
select name, unit, price from products order by sort_order;


-- ------------------------------------------------------------
-- 2. LE FORMAT DE VENTE
--
-- « bouteille 350 ml » par défaut. Si Mine de Ketchup vend à la caisse, c'est
-- ici que ça se corrige — le détaillant commande en nombre d'unités.
-- ------------------------------------------------------------
-- update products set unit = 'caisse de 12' where category = 'Ketchups';


-- ------------------------------------------------------------
-- 3. LES DÉTAILLANTS
--
-- Une ligne par commerce. Le code d'accès et le lien personnel se créent tout
-- seuls : ne rien mettre dans ces colonnes.
--
-- Le courriel sert à envoyer la confirmation de commande au détaillant ; sans
-- lui, seul Mine de Ketchup est averti. Les notes ne sont jamais montrées au
-- détaillant.
-- ------------------------------------------------------------
insert into retailers (business_name, contact_name, phone, email, notes) values
    ('Épicerie du Coin',   'Prénom Nom', '418-555-0100', 'commandes@epicerie.ca', 'Livraison le mardi'),
    ('Marché Mitis',       'Prénom Nom', '418-555-0101', 'achats@marche.ca',      null),
    ('Boucherie Padoue',   'Prénom Nom', '418-555-0102', null,                    'Pas de courriel — appeler')
on conflict do nothing;   -- relancer le bloc ne crée pas de doublon


-- ------------------------------------------------------------
-- 4. LES LIENS À ENVOYER
--
-- Le résultat se copie tel quel dans un tableur : une ligne par détaillant,
-- avec son adresse courriel et son lien personnel. C'est la liste d'envoi.
--
-- Remplacez l'adresse ci-dessous si l'app n'est pas sur minedeketchup.
-- ------------------------------------------------------------
select
    business_name                                                as commerce,
    coalesce(contact_name, '')                                   as contact,
    coalesce(email, '— pas de courriel —')                       as courriel,
    'https://minedeketchup.streamlit.app/?c=' || access_code     as lien_personnel
from retailers
where is_active = true
order by business_name;
