"""
Photos des produits : téléversées depuis le tableau de bord, stockées dans
Supabase Storage.

Le producteur choisit un fichier sur son ordinateur ou son téléphone ; on le
réduit et on le convertit en JPEG avant l'envoi. Une photo de téléphone pèse
souvent 4 à 8 Mo : les détaillants, qui commandent surtout sur mobile, ne
téléchargent ainsi qu'environ 200 Ko par produit.

Le compartiment (« bucket ») est public en LECTURE : la page de commande
affiche les photos par leur simple adresse. Seule la clé service_role, donc
le tableau de bord, peut y écrire.
"""

from __future__ import annotations

import io
import uuid

from PIL import Image, ImageOps

BUCKET = "produits"
TYPES = ["jpg", "jpeg", "png", "webp"]
COTE_MAX_PX = 1200
QUALITE_JPEG = 85


def preparer(donnees: bytes) -> bytes:
    """Redresse, réduit et convertit une image en JPEG léger."""
    with Image.open(io.BytesIO(donnees)) as source:
        # Les téléphones enregistrent l'orientation à part : sans ceci, une
        # photo prise en portrait s'afficherait couchée.
        image = ImageOps.exif_transpose(source)
        image.thumbnail((COTE_MAX_PX, COTE_MAX_PX))
        if image.mode != "RGB":
            # PNG transparent : fond blanc plutôt que noir.
            fond = Image.new("RGB", image.size, "white")
            fond.paste(image, mask=image.convert("RGBA").getchannel("A"))
            image = fond
        sortie = io.BytesIO()
        image.save(sortie, "JPEG", quality=QUALITE_JPEG, optimize=True)
    return sortie.getvalue()


def televerser(client, fichier) -> str:
    """Envoie la photo dans Supabase Storage et renvoie son adresse publique.

    `fichier` est la valeur d'un st.file_uploader. Le compartiment est créé
    au premier envoi s'il n'existe pas encore : aucune étape manuelle dans
    Supabase.
    """
    donnees = preparer(fichier.getvalue())
    chemin = f"{uuid.uuid4().hex}.jpg"
    options = {"content-type": "image/jpeg", "cache-control": "31536000"}

    stockage = client.storage
    try:
        stockage.from_(BUCKET).upload(chemin, donnees, options)
    except Exception as exc:  # noqa: BLE001 — seul « bucket absent » se rattrape
        if "not found" not in str(exc).lower():
            raise
        stockage.create_bucket(BUCKET, options={"public": True})
        stockage.from_(BUCKET).upload(chemin, donnees, options)

    return stockage.from_(BUCKET).get_public_url(chemin).rstrip("?")
