# PPR_Project
Projet de Protocole et Programmation Réseaux de Master 1
# Fonctionnement général
Le proxy est un programme qui agit comme un intermédiaire entre votre ordinateur et Internet. Il reçoit les requêtes que vous envoyez à des sites web et les transmet à ces sites, puis il transmet les réponses de ces sites à votre ordinateur. En utilisant un proxy, vous pouvez contrôler et filtrer les informations qui passent entre votre ordinateur et Internet.

# Limitations
Ce proxy ne fonctionne que pour les requêtes HTTP et non pour les requêtes HTTPS. Cela signifie qu'il ne peut pas être utilisé pour naviguer sur des sites web qui utilisent une connexion sécurisée (indiquée par le "https" dans l'adresse du site). Il ne gère que les requêtes GET et POST.

# Fonctionnalités de filtrage
Ce proxy vous permet de personnaliser votre navigation en utilisant plusieurs fonctionnalités de filtrage :

Remplacement de mots : vous pouvez spécifier des mots à remplacer par d'autres mots lors de la navigation. Par exemple, vous pouvez remplacer le mot "chat" par "chien" sur tous les sites web que vous visitez.

Suppression de mots : vous pouvez spécifier des mots à supprimer de la navigation.

Blocage d'accès à certaines URL : vous pouvez spécifier des adresses de sites web à bloquer. Ainsi, vous ne pourrez pas accéder à ces sites depuis votre ordinateur.

Suppression de certaines ressources : vous pouvez spécifier des types de fichiers à supprimer de la navigation. Par exemple, vous pouvez supprimer tous les fichiers mp4 pour éviter de charger de gros fichiers inutiles.

# Configuration
Pour utiliser le proxy il suffit de configurer votre navigateur afin qu'il utilise un proxy pour le protocole HTTP, ensuite il vous suffira simplement de run le fichier main.py.

Pour mettre à jour les paramètres de filtrage, vous pouvez vous connecter à l'adresse http://localhost:8080/proxy_config (Si vous n'arrivez pas à vous connecter il se peut que le numéro de port ne soit pas le bon, vérifier dans le fichier proxy.config quel est le numéro de port). Vous pourrez alors modifier les différentes options de filtrage et enregistrer les modifications dans le fichier proxy.config. Pour que ces modifications soient appliquées relancez le fichier main.py.
