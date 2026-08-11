# sigurdos.dev

Source for the [SigurdOS firmware](https://github.com/hermes-gadget/SigurdOS-tdeck) website.

## Stack

- HTML, CSS, and JavaScript under `public/`, with no package manager or build step.
- `server.py` uses Python's standard library to serve an exact allowlist of public assets
  and exposes the `/api/tile` map-tile proxy; the repository checkout itself is
  never used as a document root.
- Runtime services are the GitHub API for release/contributor metadata, Leaflet 1.9.4
  from unpkg (pinned with SRI), Google Fonts, OpenStreetMap standard tiles, and CARTO
  dark basemap tiles. Their availability, licences, and terms remain external to this
  repository.

## Local development

```sh
python3 server.py 8080
```

Open `http://127.0.0.1:8080/`. The same allowlist and tile-proxy boundary used in
production applies locally.

## Deploy

Nginx terminates HTTPS on the sigurdos.dev VM and forwards the site traffic to the
Python server. Push to `main`, pull on the server, and restart the managed service when
the server code or public asset allowlist changes.

## License

Project-authored website code is licensed under GPL-3.0-only. See [LICENSE](LICENSE).
Third-party components, fonts, services, map data, and imagery retain their own
licences and terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
