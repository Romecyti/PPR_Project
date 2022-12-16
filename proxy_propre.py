#!usr/bin/python3

#copyright 2022 : written by MARCHAND Célestin, PIERRET Alexandre and COQUERON Solal 

#scrypt décrivant un proxy créé dans le cadre du projet de la matière "protocole et programmation réseaux" de la 1ère année du master ISICG à L'université de Limoges

import socket
import re
from _thread import start_new_thread

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

#fonction qui traite l'entete d'une requete Connect et retourne une requete a transmettre au serveur ainsi que le numéro de port du serveur et son nom
def TraitementEnteteRequeteHTTPS(requete) :
    requete = requete.decode().split("\n") #sépare l'entete de la requête selon les lignes

    #on vient récupérer les informations du numéro de port et du nom du site sur la ligne contenant HOST
    for e in requete :
        if not re.match(r"Host:*", e, flags=re.IGNORECASE) :
            nom_serveur, num_port_serveur  = re.match(r"Host: (?P<nom_serveur>[^\s:]+)?(:(?P<num_port>\d+))?", requete[1]).group('nom_serveur','num_port')

    if num_port_serveur == None :
        probleme_lecture_entete = True
    else :
        probleme_lecture_entete = False

    proxys_response = "HTTP/1.0 200 OK" 

    return proxys_response.encode(), num_port_serveur, nom_serveur, probleme_lecture_entete

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

#fonction qui fait le traitement des requetes HTTP
def TraitementRequeteHTTP (requete, socket_requete : socket.socket) :
    #on va faire les traitements nécessaires pour nettoyer la requete et enlever les infos inutile pour le serveur 
    #ainsi que récupérer les informations nécessaire a l'envoie de la requete au serveur web
    requete, num_port_serveur, nom_serveur = TraitementEnteteRequeteHTTP(requete)
    suite_requete = b'' #si la requette est une requete POST, alors il y aura des arguments suplémentaire 
    probleme_requete = False

    #on regarde maintenant si c'est une requete GET ou POST
    if re.search('POST', requete.decode(), flags=re.IGNORECASE) :
        #dans ce cas, c'est une requete POST et l'on doit donc lire les arguments supplémentaire de la requête
        #ceux-ci se trouvent dans un bloc supplémentaire de la même forme qu'une requête
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

#fonction qui s'occupe de faire le lien TLS entre le serveur web et le navigateur
def ReceptionReponseTLS (socket_serveur, socket_requete):
    while 1 :
        try :
            message_serveur = socket_serveur.recv(1024)
            print("reponse serveurTLS : ", message_serveur, "\n")
            socket_requete.sendall(message_serveur)
        except Exception:
            break 

    return

#fonction qui fait le traitement des requetes HTTPS
def TraitementRequeteHTTPS (requete, socket_requete : socket.socket) :
    #on va créer une socket connectée au serveur web
    reponse_proxys, num_port_serveur, nom_serveur, probleme_lecture_entete = TraitementEnteteRequeteHTTPS(requete)

    if not probleme_lecture_entete :
        socket_serveur, probleme_creation_socket_serveur = CreationSocketServeur(num_port_serveur, nom_serveur)
        if not probleme_creation_socket_serveur :
            #on renvoie l'aquitement de la requete
            print("reponse proxy : \n", reponse_proxys)
            socket_requete.sendall(reponse_proxys) #aquitement message à créer


            #une fois la requete acceptée, on va faire le pont entre le navigateur et le serveur web
            socket_requete.settimeout(100.0)
            socket_serveur.settimeout(100.0)

            start_new_thread(ReceptionReponseTLS, (requete, socket_requete,))

            while 1 :
                try :
                    message_navigateur = socket_requete.recv(1024)
                    print("requete navigateur : ", message_navigateur, "\n")
                    socket_serveur.sendall(message_navigateur)
                except Exception:
                    break
            
            socket_serveur.close()
        #end if
    #end if
    return


#fonction qui fait le traitement des requete donnée sur une socket 
def TraitementRequete(socket_requete) :
    (requete, probleme_requete) = LectureRequete(socket_requete)

    #ici on peut faire filtrage sur url
    #ne pas oublier de renvoyer une erreur si le site n'est pas accepté

    #on regarde si la lecture de la requete s'est déroulé normalement
    if not probleme_requete :
        #dans ce cas, on peut faire notre traitement
        #on va d'abord regarder quel est le protocole (http ou https)
        if (re.search('CONNECT', requete.decode())) :
            #dans ce cas, c'est le porotocole https
            #pour le moment, on ne le traite pas 

            TraitementRequeteHTTPS(requete, socket_requete)
        else :

            #ici on peut faire filtrage sur ressources acceptées

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