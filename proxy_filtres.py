import re
import proxy_config

#############################################
#                                           #
#          FiltreBlacklistRessources        #
#                                           #
#############################################
#fonction qui effectue un filtre sur les ressources acceptées et renvoies un booleen à false si la requete ne peut être envoyer (i.e. aucune ressources demandé n'est accepté)
def FiltreBlacklistRessources(entete_requete) :
    requete_autoriser = True
    entete_requete = entete_requete.decode().split("\n")

    num_ligne_ressource = -1
    for i in range(len(entete_requete)) :
        if re.match(r'Accept:[\s\S]+', entete_requete[i]) :
            num_ligne_ressource = i
            break

    #on s'assure d'avoir trouvé la ligne des ressources, sinon il n'y a pas de précision donc on refuse la requete
    if num_ligne_ressource == -1 :
        return "\n".join(entete_requete).encode(), False

    #on fait maintenant un traitement sur la lignes des ressources
    tableau_ressources_demander, suite_ligne = re.search(r'Accept: (?P<ressources>[^;]+)?(?P<suiteligne>[\s\S])?', entete_requete[num_ligne_ressource]).group('ressources','suiteligne')
    tableau_ressources_demander = tableau_ressources_demander.split(",")
    blacklisted_resources = proxy_config.LectureConfigArray("options.config")["resources_blacklist"]

    # Est ce que les ressources sont accepté ?
    tableau_ressources_accepter = []
    for ressource in tableau_ressources_demander :
        ressource_interdites = False
        for blacklisted_res in blacklisted_resources :
            if blacklisted_res == ressource :
                ressource_interdites = True
                break
        if not ressource_interdites :
            tableau_ressources_accepter.append(ressource)

    #maintenant que le traitement est fait, si aucune ressource n'a été accepté, on refuse la requete
    if len(tableau_ressources_accepter) < 1 :
        return "\n".join(entete_requete).encode(), False

    #sinon on va reconstruire la requete avec les bonnes ressources
    ressources_accepter = ",".join(tableau_ressources_accepter)
    entete_requete[num_ligne_ressource] = "Accept: " + ressources_accepter
    entete_requete = "\n".join(entete_requete)

    return entete_requete.encode(), requete_autoriser

#############################################
#                                           #
#          FiltreBlacklistServeur           #
#                                           #
#############################################
#fonction qui effectue un filtre sur le nom du serveur web
def FiltreBlacklistServeur(entete_requete) :
    accept = True
    nom_serveur = ""
    tab_requete = entete_requete.decode().split("\n")
    blacklisted_url = proxy_config.LectureConfigArray("options.config")["server_blacklist"]

    for e in tab_requete :
        if re.match(r'Host:[\s\S]*', e) :
            nom_serveur = re.search(r'Host: (?P<nom_serveur>[^\s:]+)?(:\d+)?', e).group('nom_serveur')

    for e in blacklisted_url :
        if e=="":
            continue
        if re.match(e, nom_serveur):
            accept = False

    return accept

#############################################
#                                           #
#           FiltreSuppressionMots           #
#                                           #
#############################################
#fonction qui effectue la suppression des mots voulu par l'utilisateur
def FiltreSuppressionMots(corps_requete : bytearray) :
    words_to_delete = proxy_config.LectureConfigArray("options.config")["words_to_delete"]

    for word in words_to_delete :
        corps_requete = re.sub(word.encode(), b'', corps_requete)

    return corps_requete

#############################################
#                                           #
#          FiltreRemplacementMots           #
#                                           #
#############################################
#fonction qui effectue le remplacement des mots voulu par l'utilisateur
def FiltreRemplacementMots(corps_requete : bytearray):
    words_to_replace = proxy_config.LectureConfigArray("options.config")["words_to_replace"]

    #on s'assure que la taille du tableau soit bien un multiple de 2 
    if (len(words_to_replace) % 2) == 1 :
        words_to_replace.append("")

    for i in range(0,len(words_to_replace), 2) :
        corps_requete = re.sub(words_to_replace[i].encode(), words_to_replace[i+1].encode(), corps_requete)

    return corps_requete

#############################################
#                                           #
#            AppelFiltresSurMots            #
#                                           #
#############################################
#fonction qui eeffectue l'appel au fonction de remplacement et de suppression des mots et modifie ensuite l'entête pour faire correspondre la taille de la réponse a la taille après modification
def CallFiltre(requete : bytearray) : 
    entete_requete, corps_requete = re.search(rb'(?P<entete>[\s\S]+\r\n\r\n)?(?P<corps>[\s\S]+)?', requete).group('entete', 'corps')
    
    #cas si la réponse ne contient que une entete
    if corps_requete == None :
        return requete

    #sinon, alors la réponse contient bien des données et on peut les modifier
    corps_requete = FiltreSuppressionMots(corps_requete)
    corps_requete = FiltreRemplacementMots(corps_requete)

    #on doit maintenant modifier l'indication de taille des données située dans l'entete
    entete_requete = entete_requete.split(b'\n')

    for i in range(len(entete_requete)) :
        if re.match(rb'Content-Length:[\s\S]+', entete_requete[i]) :
            entete_requete[i] = b'Content-Length: ' + str(len(corps_requete)).encode() + b'\r'
            break
    
    entete_requete = b'\n'.join(entete_requete)

    return (entete_requete + corps_requete)
