#!usr/bin/python3
#copyright 2022 : written by MARCHAND Célestin, PIERRET Alexandre and COQUERON Solal 
#script décrivant un proxy créé dans le cadre du projet de la matière "protocole et programmation réseaux" de la 1ère année du master ISICG à L'université de Limoges

import socket
import re
from _thread import start_new_thread

tableau_site_interdit = []
tableau_type_ressource_interdites = []

def LectureConfigArray(path):

    file = open(path, "r")
    lines = file.read().split("\n")
    values = {}

    for line in lines:
        key_values = line.split(":")
        values[key_values[0]] = CsvSplit(key_values[1], ",")

    return values

def LectureConfigString(path):

    file = open(path, "r")
    lines = file.read().split("\n")
    values = {}

    for line in lines:
        key_values = line.split(":")
        values[key_values[0]] = key_values[1]

    return values
    
def CsvSplit(str, sep):

    array = []
    current = ""
    str += '\n'

    for i in range(len(str)):
    
        if str[i - 1] == '\\' and str[i] == sep:
            current += sep
        elif str[i - 1] != '\\' and str[i] == sep:
            array.append(current)
            current = ""
        elif i + 1 < len(str) and str[i] == '\\' and str[i + 1] == sep:
            continue
        elif str[i] == '\n':
            array.append(current)
            current = ""
        else:
            current += str[i]

    return array

def ReadHTMLFile(path, dict):
    file = open(path, "r")
    html = file.read()

    for i in dict:
        html = html.replace("{{" + i + "}}", dict[i])

    return html

def SendHTMLToClient(path, socket_client, dict):
    html = ReadHTMLFile(path, dict)
    reponse = "HTTP/1.1 200 OK\r\n"\
              "Connection: Keep-Alive\r\n"\
              "Content-Length: " + str(len(html)) + "\r\n"\
              "Content-Type: text/html; charset=utf-8\r\n"\
              "\n"
    reponse += html
    socket_client.sendall(reponse.encode())

#fonction qui créait la socket principale du proxy
def CreateProxysSocket(adresse_ip_proxy, port_socket_proxy) :
    tsap_proxy = (adresse_ip_proxy, port_socket_proxy)

    #création et paramétrisation de la socket
    socket_proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1) #permet de ne pas attendre pour pouvoir réutiliser ce port
    socket_proxy.bind(tsap_proxy) #accroche la socket au numro du port de la machine concernée
    socket_proxy.listen(1)

    return socket_proxy

#fonction qui lit une requete (que ce soit une entete de réponse TCP ou une requete TCP)
def LectureRequete(socket_tcp):
    requete = b""
    probleme_lecture = False

    ligne_courante = b""
    #boucle de lecture de l'entete
    while 1:
        caractere_courant = socket_tcp.recv(1)
        if not caractere_courant :
            probleme_lecture = True
            break
        if caractere_courant == b'\r' :
            ligne_courante += caractere_courant
            caractere_courant = socket_tcp.recv(1)
            if caractere_courant == b'\n' :
                ligne_courante += caractere_courant
                requete += ligne_courante
                if ligne_courante == b'\r\n' :
                    break #fin de l'entete
                else :
                    ligne_courante = b'' #si ce n'est pas la fin, on remet la ligne courante à zéro
            else :
                ligne_courante += caractere_courant
        else :
            ligne_courante += caractere_courant #sinon c'est caractere lambda
        
    return (requete, probleme_lecture)

#fonction qui lit les arguments d'une requete post à partir de son entete
def LectureArgumentsRequetePost(entete_requete_post, socket_tcp) :
    #il faut dans un premier temps repérer la taille des arguments
    #définit soit en taille, soit avec une balise de fin
    probleme_lecture_argument_requete = False
    argument_requete = b''

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
                argument_requete += socket_tcp.recv(8196)
                taille_information -= 8196
            argument_requete += socket_tcp.recv(taille_information)
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
                        argument_requete += ligne_courante
                        if ligne_courante == ligne_balise_fin :
                            ligne_courante = socket_tcp.recv(2) #on vient recevoir le '\r\n' qui est la fin des arguments
                            #on vérifie que ce sont bien ces deux caractères qui viennent d'arriver
                            if ligne_courante == b'\r\n' :
                                probleme_lecture_argument_requete = True
                            else :
                                argument_requete += ligne_courante
                            break #fin de l'entete
                        else :
                            ligne_courante = b'' #si ce n'est pas la fin, on remet la ligne courante à zéro
                    else :
                        ligne_courante += caractere_courant
                else :
                    ligne_courante += caractere_courant #sinon c'est caractere lambda


    return argument_requete, probleme_lecture_argument_requete

#fonction qui lit une entete TCP et qui retourne la taille des données qui suivent cette entete
def LectureEnteteTCP(socket_tcp):
    entete, probleme_lecture = LectureRequete(socket_tcp)

    if probleme_lecture :
        return entete, None, probleme_lecture
    else :
        #s'il n'y a pas de problème de lecture de l'entete TCP
        #alors on va chercher la taille des données qui suivent cette entete
        lignes_entete = entete.decode().split("\n")
        taille_information = None

        for e in lignes_entete :
            if re.match(r"Content-Length:[\s\S]*", e, re.IGNORECASE) :
                taille_information = re.search(r"Content-Length: (?P<tailleinformation>[0-9]+)?", e).group('tailleinformation')
         
        if taille_information != None :
            taille_information = int(taille_information)
        else :
            taille_information = 0

        return (entete, taille_information, probleme_lecture)

#fonction qui traite l'entete d'une requete et retourne une entete nettoyer des parametre proxy ainsi que le numéro de port du serveur web et de son nom
def TraitementEnteteRequeteHTTP(requete) :
    requete = requete.decode().split("\n") #sépare l'entete de la requête selon les lignes

    nom_serveur = re.match(r"Host: (?P<nom_serveur>[^\s:]+)?(:\d+)?", requete[1]).group('nom_serveur')

    # Si localhost, on renvoie directement le resultat
    if(nom_serveur == "localhost"):
        return (requete, 8080, nom_serveur)

    #on vient récupérer les informations importante situé sur la première ligne
    (serveur_methode_requete, num_port_serveur, serveur_file_access) = re.match(r"(?P<method>[^\s]+) ([^\s]*"+nom_serveur+r")(:(?P<num_Port>\d+))?(?P<file_access>[^\s]+)? ([^\s]+)",requete[0]).group('method','num_Port','file_access')
    if num_port_serveur == None:
        num_port_serveur = "80"

    if serveur_file_access == None:
        serveur_file_access = ""

    #on nettoye la première ligne en la reformattant au format http (version 1.0)
    requete[0] = serveur_methode_requete + " " + serveur_file_access + " HTTP/1.0\r"

    #on enleve maintenant les lignes ne concernant que le proxy :
    proxys_request = []
    for e in requete :
        if not re.match(r"Connection: Keep-Alive[\s\S]*|Proxy-Connection: Keep-Alive[\s\S]*|Accept-Encoding: gzip[\s\S]*", e, flags=re.IGNORECASE) :
            proxys_request.append(e)
    
    requete = "\n".join(proxys_request)
    requete = requete.encode()

    return (requete, num_port_serveur, nom_serveur)

#fonction qui créer une socket de connexion à un serveur d'après son numéro de port et son nom et retourne cette socket ainsi que la réussite de la création
def CreationSocketServeur(num_port_serveur, nom_serveur) :
    probleme_creation_socket_serveur = False
    serveur_adresse_ip = socket.gethostbyname(nom_serveur)
    socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try :
        socket_serveur.connect((serveur_adresse_ip, int(num_port_serveur)))
    except Exception as e :
        print(e.args)
        probleme_creation_socket_serveur = True

    return (socket_serveur, probleme_creation_socket_serveur)

#fonction qui effectue un filtre sur le nom du serveur web
def FiltreAcceptantServeur(entete_requete) :
    bool_requete_accepter = True

    nom_serveur = ""
    tab_requete = entete_requete.decode().split("\n")
    for e in tab_requete :
        if re.match(r'Host:[^\s\S]', e) :
            nom_serveur = re.search(r'Host: (?P<nom_serveur>[^\s:]+)?(:\d+)?', e).group('nom_serveur')

    for e in tableau_site_interdit :
        if re.match(e, nom_serveur):
            bool_requete_accepter = False


    return bool_requete_accepter

#fonction qui effectue un filtre sur les ressources acceptées et renvoies un booleen à false si la requete ne peut être envoyer (i.e. aucune ressources demandé n'est accepté)
def FiltreAcceptantRessources(entete_requete) :
    requete_autoriser = True
    entete_requete = entete_requete.decode().split("\n")

    num_ligne_ressource = -1
    for i in range(len(entete_requete)) :
        if re.match(r'Accept:[\s\S]+', entete_requete[i]) :
            num_ligne_ressource = i
            break

    #on s'assure d'avoir trouvé la ligne des ressources, sinon il n'y à pas de précision donc on refuse la requete
    if num_ligne_ressource == -1 :
        return "\n".join(entete_requete).encode(), False

    #on fait maintenant un traitement sur la lignes des ressources
    tableau_ressources_demander, suite_ligne = re.search(r'Accept: (?P<ressources>[^;]+)?(?P<suiteligne>[\s\S])?', entete_requete[num_ligne_ressource]).group('ressources','suiteligne')
    tableau_ressources_demander = tableau_ressources_demander.split(",")

    tableau_ressources_accepter = []
    for ressource in tableau_ressources_demander :
        ressource_interdites = False
        for e in tableau_type_ressource_interdites :
            if re.match(r'[\s\S]+/' + e ) :
                ressource_interdites = True
                break
        if not ressource_interdites :
            tableau_ressources_accepter.append(ressource)

    #maintenant que le traitement est fait, si aucune ressource n'a été accepté, on refuse la requete
    if len(tableau_ressources_accepter) < 1 :
        return "\n".join(entete_requete).encode(), False

    #sinon on va reconstruire la requete avec les bonnes ressources
    ressources_accepter = ",".join(tableau_ressources_accepter)
    entete_requete[num_ligne_ressource] = "Accept: " + ressources_accepter + suite_ligne

    entete_requete = "\n".join(entete_requete)

    return entete_requete.encode(), requete_autoriser

#fonction qui fait le traitement des requetes HTTP
def TraitementRequeteHTTP (requete, socket_requete : socket.socket) :
    #on va faire les traitements nécessaires pour nettoyer la requete et enlever les infos inutile pour le serveur 
    #ainsi que récupérer les informations nécessaire a l'envoie de la requete au serveur web
    requete, num_port_serveur, nom_serveur = TraitementEnteteRequeteHTTP(requete)
    suite_requete = b'' #si la requette est une requete POST, alors il y aura des arguments suplémentaire 
    probleme_requete = False

    # Si requete GET
    # decode provoque une erreur c'est pour ca que c'est fait comme ca
    if (re.search('GET', requete.decode())) :
        if nom_serveur == "localhost":
                configs = LectureConfigString("options.config")
                dict = {"configuration_port": configs["port"], 
                        "configuration_words_to_replace": configs["words_to_replace"], 
                        "configuration_url_blacklist": configs["url_blacklist"], 
                        "configuration_resources_blacklist": configs["resources_blacklist"]}
                SendHTMLToClient("admin.html", socket_requete, dict)
                return

    #Si requete POST - ya une erreur ici
    if (re.search('POST', requete.decode())) :
        #dans ce cas, c'est une requete POST et l'on doit donc lire les arguments supplémentaire de la requête
        #ceux-ci se trouvent dans un bloc supplémentaire de la même forme qu'une requête
        print("test")
        suite_requete, probleme_requete = LectureArgumentsRequetePost(requete, socket_requete)
    #end if

    #on regarde s'il y a eu un problème dans la lecture des arguments de la requete POST
    #(si jamais on avait une requete GET, alors cela ne changera pas la requete de base)
    if not probleme_requete :
        requete += suite_requete
        socket_serveur, probleme_creation_socket_serveur = CreationSocketServeur(num_port_serveur, nom_serveur)

        #on regarde si la socket vers le serveur à pu être créée
        if not probleme_creation_socket_serveur :
            #si oui, alors on va envoyer la requete au serveur
            socket_serveur.sendall(requete)

            #on lit ensuite l'entete de la réponse du serveur
            entete_reponse, taille_reponse, probleme_lecture_entete_reponse = LectureEnteteTCP(socket_serveur)

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
    (requete, probleme_requete) = LectureRequete(socket_requete)

    #ici on peut faire filtrage sur url
    if not FiltreAcceptantServeur(requete) :
        #ne pas oublier de renvoyer une erreur si le site n'est pas accepté !!!!!!!!!!
        socket_requete.close()
        return

    #on regarde si la lecture de la requete s'est déroulé normalement
    if not probleme_requete :
        #dans ce cas, on peut faire notre traitement
        #on va d'abord regarder quel est le protocole (http ou https)
        if (re.search('CONNECT', requete.decode())) :
            #dans ce cas, c'est le porotocole https
            #pour le moment, on ne le traite pas 
            print('requete https : \n', requete, '\n')
        else :

            #ici on peut faire filtrage sur ressources acceptées
            requete, requeteAccepter = FiltreAcceptantRessources(requete)
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

#fonction décrivant le proxy
def main(adresse_ip_proxy = "", port_socket_proxy = 8080) :
    socket_proxy = CreateProxysSocket(adresse_ip_proxy, port_socket_proxy)

    #début d'écoute des requêtes faites au proxy
    while 1 :
        (socket_requete, tsap_requete) = socket_proxy.accept() #retourne une socket et le tsap associé a celle-ci (inutile ici) lorsqu'une connexion à lieu sur le port
        #start_new_thread(TraitementRequete, (socket_requete,))
        TraitementRequete(socket_requete)
    #end while

    socket_proxy.close()
    return 0


#on appelle le main si jamais le script à bien été lancé en scrypt principale
if __name__ == "__main__" :
    main()