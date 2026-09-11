# assets/

Dossier optionnel pour le logo officiel de Mine de Ketchup.

Par défaut, l'app dessine elle-même le lettrage « MINE / pics croisés /
DE KETCHUP » (voir `logo_markup()` dans `lib/branding.py`) : il est net à
toutes les tailles et prend la couleur crème du thème sombre.

Pour utiliser le fichier officiel à la place, déposez-le ici sous un nom
commençant par `logo` :

| Fichier | Effet |
|---|---|
| `logo.png`, `logo.svg`, `logo.jpg`, `logo.webp` | Logo **sombre sur fond clair** (le fichier officiel). Il est automatiquement inversé pour ressortir en clair sur le thème sombre. |
| `logo-blanc.png` (ou `logo-white.png`) | Logo **déjà clair**, affiché tel quel, sans inversion. |

Le premier fichier trouvé par ordre alphabétique est utilisé. Aucun changement
de code n'est nécessaire.

Conseil : rognez les marges blanches autour du lettrage avant de déposer le
fichier. L'image est affichée à 66 px de haut ; un fichier carré avec beaucoup
de blanc autour donnerait un logo visuellement minuscule.
