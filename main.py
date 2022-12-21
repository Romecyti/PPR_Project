import proxy_http
import proxy_config
from _thread import start_new_thread

#############################################
#                                           #
#                  Main                     #
#                                           #
#############################################
def main() :
    adresse_ip_proxy = ""
    port_socket_proxy = 8080
    
    config_port = proxy_config.LectureConfigString("options.config")["port"]
    if(config_port != ""):
        port_socket_proxy = int(config_port)
    socket_proxy = proxy_http.CreateProxysSocket(adresse_ip_proxy, port_socket_proxy)
    print("Proxy {ip:" + adresse_ip_proxy + ", port:" + str(port_socket_proxy) + "}")

    #début d'écoute des requêtes faites au proxy
    while 1 :
        (socket_requete, tsap_requete) = socket_proxy.accept() #retourne une socket et le tsap associé a celle-ci (inutile ici) lorsqu'une connexion à lieu sur le port
        start_new_thread(proxy_http.TraitementRequete, (socket_requete,))
        #proxy_http.TraitementRequete(socket_requete)
    #end while

    socket_proxy.close()
    return 0


#on appelle le main si jamais le script à bien été lancé en scrypt principale
if __name__ == "__main__" :
    main()