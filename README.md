# LibraryOS

LibraryOS is the Library Management System for this `ft_transcendence`
project. The application runs as a React frontend behind an Nginx HTTPS
gateway, with FastAPI and PostgreSQL on the private Docker network.

## Local startup

From this directory:

```bash
docker compose up --build
```

Open <https://localhost>. The local certificate is self-signed for
development. A browser may show a trust warning on first visit; accepting the
local exception is sufficient for a local evaluation. The certificate is kept
in the named `certs_data` volume, so recreating the web container does not
silently replace a certificate that has already been trusted.

For a persistent OS/browser trust setup, copy the public certificate out of
the running container and import only that certificate into the local trust
store:

```bash
docker compose cp web:/etc/nginx/certs/localhost.crt ./localhost.crt
```

Never copy or import the private key. The certificate covers `localhost` and
`127.0.0.1`; use the matching hostname when opening the application.

The API is intentionally not published as a host port. Browser traffic goes
through Nginx over HTTPS, and backend secrets remain in the API container.
