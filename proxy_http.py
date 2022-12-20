import re
import socket
import proxy_html
import proxy_tcp
import proxy_filtres
import proxy_config

#fonction qui créer la socket principale du proxy
def CreateProxysSocket(adresse_ip_proxy, port_socket_proxy) :
    tsap_proxy = (adresse_ip_proxy, port_socket_proxy)
    socket_proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socket_proxy.bind(tsap_proxy)
    socket_proxy.listen(1)
    return socket_proxy

#fonction qui lit les arguments d'une requete post à partir de son entete
def LectureArgumentsRequetePost(entete_requete_post, socket_tcp) :
    #il faut dans un premier temps repérer la taille des arguments
    #définit soit en taille, soit avec une balise de fin
    probleme_lecture_argument_requete = False
    arguments_requete = b''

    lignes_entete = entete_requete_post.decode().split("\n")
    taille_information = None
    balise_fin_argument = ''

    for e in lignes_entete :
        if re.match(r"Content-Length:[\s\S]*", e, re.IGNORECASE) :
            taille_information = re.search(r"Content-Length: (?P<tailleinformation>[0-9]+)?", e).group('tailleinformation')
        if re.match(r"Content-Length:[\s\S]*", e, re.IGNORECASE) : 
            balise_fin_argument = re.search(r"Content-Length:[\s\S]+(boundary=\"(?P<boundaryTag>[\s]+)\")?[\s\S]*", e).group('boundaryTag')

    #on s'assure que l'entête contenait bien l'un des deux argument
    if (taille_information == None) and (balise_fin_argument == '') :
        probleme_lecture_argument_requete = True
    else :
        #si on a au moins l'un des deux argument, on va pouvoir traiter les arguments
        if taille_information != None :
            #soit on lis les arguments par leur taille :
            taille_information = int(taille_information)
            while  taille_information > 8196 :
                arguments_requete += socket_tcp.recv(8196)
                taille_information -= 8196
            arguments_requete += socket_tcp.recv(taille_information)
        else :
            #sinon on va lire les argument jusqu'à la balise "--{balise_fin_argument}--" plus une ligne vide
            caractere_courant = b''
            ligne_courante = b''
            ligne_balise_fin = b'--' + balise_fin_argument.encode() + b'--\r\n'

            while 1:
                caractere_courant = socket_tcp.recv(1)
                if not caractere_courant :
                    probleme_lecture_argument_requete = True
                    break
                if caractere_courant == b'\r' :
                    ligne_courante += caractere_courant
                    caractere_courant = socket_tcp.recv(1)
                    if caractere_courant == b'\n' :
                        ligne_courante += caractere_courant
                        arguments_requete += ligne_courante
                        if ligne_courante == ligne_balise_fin :
                            ligne_courante = socket_tcp.recv(2) #on vient recevoir le '\r\n' qui est la fin des arguments
                            #on vérifie que ce sont bien ces deux caractères qui viennent d'arriver
                            if ligne_courante == b'\r\n' :
                                probleme_lecture_argument_requete = True
                            else :
                                arguments_requete += ligne_courante
                            break #fin de l'entete
                        else :
                            ligne_courante = b'' #si ce n'est pas la fin, on remet la ligne courante à zéro
                    else :
                        ligne_courante += caractere_courant
                else :
                    ligne_courante += caractere_courant #sinon c'est caractere lambda


    return arguments_requete, probleme_lecture_argument_requete

#fonction qui traite l'entete d'une requete et retourne une entete nettoyer des parametre proxy ainsi que le numéro de port du serveur web et de son nom
def TraitementEnteteRequeteHTTP(requete) :
    decoded_requete_http = requete.decode().split("\n")
    nom_serveur = re.match(r"Host: (?P<nom_serveur>[^\s:]+)?(:\d+)?", decoded_requete_http[1]).group('nom_serveur')

    # Si localhost, on return directement la requête de base
    if(nom_serveur == "localhost"):
        return (requete, 8080, nom_serveur)

    #on vient récupérer les informations importante situé sur la première ligne
    (serveur_methode_requete, num_port_serveur, serveur_file_access) = re.match(r"(?P<method>[^\s]+) ([^\s]*"+nom_serveur+r")(:(?P<num_Port>\d+))?(?P<file_access>[^\s]+)? ([^\s]+)",decoded_requete_http[0]).group('method','num_Port','file_access')
    if num_port_serveur == None:
        num_port_serveur = "80"

    if serveur_file_access == None:
        serveur_file_access = ""

    #on nettoye la première ligne en la reformattant au format http (version 1.0)
    decoded_requete_http[0] = serveur_methode_requete + " " + serveur_file_access + " HTTP/1.0\r"

    #on enleve maintenant les lignes ne concernant que le proxy :
    proxys_request = []
    for e in decoded_requete_http :
        if not re.match(r"Connection: Keep-Alive[\s\S]*|Proxy-Connection: Keep-Alive[\s\S]*|Accept-Encoding: gzip[\s\S]*", e, flags=re.IGNORECASE) :
            proxys_request.append(e)
    decoded_requete_http = "\n".join(proxys_request)
    encoded_requete_http = decoded_requete_http.encode()

    return (encoded_requete_http, num_port_serveur, nom_serveur)

def SendPostResult(socket_requete, result):

    encoded_result = result.encode()

    post_reponse = "HTTP/1.1 200 OK\n"
    post_reponse += "Content-Length: " + str(len(encoded_result)) + "\n"
    post_reponse += "Content-Type: text/html\n"
    post_reponse += result + "\n"

    socket_requete.sendall(post_reponse.encode())
    return

#fonction qui fait le traitement des requetes HTTP
def TraitementRequeteHTTP (requete, socket_requete : socket.socket) :
    #on va faire les traitements nécessaires pour nettoyer la requete et enlever les infos inutile pour le serveur 
    #ainsi que récupérer les informations nécessaire a l'envoie de la requete au serveur web
    requete, num_port_serveur, nom_serveur = TraitementEnteteRequeteHTTP(requete)
    suite_requete = b'' #si la requette est une requete POST, alors il y aura des arguments suplémentaire 
    probleme_requete = False

    # Si requete GET
    if (re.search('GET', requete.decode())):

         # Si c'est une requête de proxy_config
        if nom_serveur == "localhost":
            array_requete = requete.decode().split("\n")
            requete_first_line = array_requete[0].split(" ")
            ressource = requete_first_line[1]
            if(len(requete_first_line) == 3):
                if(ressource == "/proxy_config"):
                    print("Requete GET : \n\tPage de configuration localhost:8080/proxy_config\n")
                    configuration = proxy_config.LectureConfigString("options.config")
                    dict = {"configuration_port": configuration["port"], 
                            "configuration_words_to_replace": configuration["words_to_replace"], 
                            "configuration_words_to_delete": configuration["words_to_delete"], 
                            "configuration_server_blacklist": configuration["server_blacklist"],
                            "configuration_resources_blacklist": configuration["resources_blacklist"]}
                    proxy_html.SendHTMLToClient("admin.html", socket_requete, dict)
                    return

    #Si requete POST
    if (re.search('POST', requete.decode())):
        #dans ce cas, c'est une requete POST et l'on doit donc lire les arguments supplémentaire de la requête
        #ceux-ci se trouvent dans un bloc supplémentaire de la même forme qu'une requête
        arguments_requete, probleme_requete = LectureArgumentsRequetePost(requete, socket_requete)
        decoded_arguments_requete = arguments_requete.decode().replace("\r\n", "\n").split("\n")
        
        # Si c'est une requête de proxy_config
        if nom_serveur == "localhost":
            array_requete = requete.decode().split("\n")
            requete_first_line = array_requete[0].split(" ")
            ressource = requete_first_line[1]
            if(len(requete_first_line) == 3):
                if(ressource == "/proxy_config"):
                    print("Requete POST : \n\tPage de configuration localhost:8080/proxy_config\n")
                    # Si envoie de configuration
                    taille_config_param = len(decoded_arguments_requete)
                    if(taille_config_param >= 7 and decoded_arguments_requete[1] == "Content-Disposition: form-data; name=\"configuration\""):
                        config_param_value = "\n".join(decoded_arguments_requete[3:len(decoded_arguments_requete) - 3])
                        proxy_config.WriteConfigString("options.config", config_param_value)
                        SendPostResult(socket_requete, "yes")
                    else:
                        SendPostResult(socket_requete, "no")
                    return

    #on regarde s'il y a eu un problème dans la lecture des arguments de la requete POST
    #(si jamais on avait une requete GET, alors cela ne changera pas la requete de base)
    if not probleme_requete :
        requete += suite_requete
        socket_serveur, probleme_creation_socket_serveur = proxy_tcp.CreationSocketServeur(num_port_serveur, nom_serveur)

        #on regarde si la socket vers le serveur à pu être créée
        if not probleme_creation_socket_serveur :
            #si oui, alors on va envoyer la requete au serveur
            socket_serveur.sendall(requete)

            #on lit ensuite l'entete de la réponse du serveur
            entete_reponse, taille_reponse, probleme_lecture_entete_reponse = proxy_tcp.LectureEnteteTCP(socket_serveur)

            if not probleme_lecture_entete_reponse :
                #s'il n'y a pas eu de problème lors de la lecture de l'entete de réponse, on peut continuer la lecture de la réponse
                reponse = entete_reponse
                taille_reponse += len(entete_reponse) 
                while taille_reponse > len(reponse):
                    reponse += socket_serveur.recv(8192)
                #end while

                #s'assure de ne pas avoir reçu trop d'informations
                if taille_reponse < len(reponse) :
                    reponse = reponse[0:taille_reponse]

                #ici on peut faire traitement sur données réceptionnées 
                #on peut faire des changement dans le texte et tout ça 
                #attention a ne pas oubier de modifier la taille des données en réception si modification !!!!!!!!! (taille du message global moins taille entete message)

                #on envoie ensuite toute la réponse au navigateur
                #print(reponse, "\n\n")
                socket_requete.sendall(reponse)
            else :
                print("problème lecture entete réponse\n\n")
            #end if
        else :
            print("problème création socket serveur\n\n")
        #end if
    #end if
    return 

#fonction qui fait le traitement des requete donnée sur une socket 
def TraitementRequete(socket_requete) :
    (requete, probleme_requete) = proxy_tcp.LectureRequete(socket_requete)

    #ici on peut faire filtrage sur url
    if not proxy_filtres.FiltreBlacklistServeur(requete) :
        #ne pas oublier de renvoyer une erreur si le site n'est pas accepté !!!!!!!!!!
        socket_requete.close()
        return

    #on regarde si la lecture de la requete s'est déroulé normalement
    if not probleme_requete :
        #dans ce cas, on peut faire notre traitement
        #on va d'abord regarder quel est le protocole (http ou https)
        if (re.search('CONNECT', requete.decode())):
            #dans ce cas, c'est le protocole https
            #pour le moment, on ne le traite pas 
            print('Requête : \n', requete, '\n')
        else :
            #ici on peut faire filtrage sur ressources acceptées
            requete, requeteAccepter = proxy_filtres.FiltreBlacklistRessources(requete)
            if not requeteAccepter :
                #ne pas oublier de renvoyer une erreur si le site n'est pas accepté !!!!!!!!!!
                socket_requete.close()
                return
            #dans ce cas, c'est une requete http
            TraitementRequeteHTTP( requete, socket_requete)

        #end if
    #end if
    #le traitement de la requete est finit, on peut fermer la socket et reccomencer la boucle
    socket_requete.close()
    return