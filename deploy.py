from pyinfra.operations import server

IMAGE = "ghcr.io/moeness77/location-voiture:latest"

server.shell(
    name="Créer le réseau",
    commands=["docker network inspect appnet >/dev/null 2>&1 || docker network create appnet"],
)

server.shell(
    name="Démarrer la base (si absente, données conservées dans le volume)",
    commands=[
        "docker inspect db >/dev/null 2>&1 || docker run -d --name db --network appnet "
        "--restart unless-stopped -e POSTGRES_USER=demo -e POSTGRES_PASSWORD=demopass "
        "-e POSTGRES_DB=demodb -v pgdata:/var/lib/postgresql/data postgres:16-alpine"
    ],
)

server.shell(name="Pull de la dernière image", commands=[f"docker pull {IMAGE}"])

server.shell(
    name="Arrêter l'ancien conteneur",
    commands=["docker stop devops-app || true", "docker rm devops-app || true"],
)

server.shell(
    name="Démarrer le nouveau conteneur",
    commands=[
        f"docker run -d --name devops-app --network appnet -p 3000:3000 --restart unless-stopped "
        f"-e DB_HOST=db -e DB_USER=demo -e DB_PASSWORD=demopass -e DB_NAME=demodb {IMAGE}"
    ],
)
