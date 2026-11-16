# Setup del profilo GitHub

Questo repo diventa il README del tuo profilo. GitHub lo mostra in cima a
github.com/paololorizzo quando il repo si chiama **esattamente come il tuo username**.

## 1. Crea il repo

1. Vai su https://github.com/new
2. Nome repository: `paololorizzo` (GitHub ti mostra il messaggio "special repository")
3. Pubblico, **senza** README iniziale → Create

## 2. Carica i file

```bash
cd paololorizzo-profile        # la cartella estratta dallo zip
git init -b main
git add .
git commit -m "feat: animated profile README"
git remote add origin git@github.com:paololorizzo/paololorizzo.git
git push -u origin main
```

## 3. Abilita la Action

- Repo → **Settings → Actions → General → Workflow permissions** → "Read and write permissions" → Save
- Repo → **Actions → Update profile cards → Run workflow**

Dopo circa un minuto la Action scarica i tuoi contributi reali, rigenera le card e fa il commit.
Da lì in poi gira da sola ogni notte.

**Opzionale, per contare anche i contributi privati:**
1. Profilo → Settings → Public profile → spunta "Include private contributions on my profile".
2. Crea un fine-grained token (Settings → Developer settings → Fine-grained tokens) con accesso in sola lettura.
3. Salvalo nel repo come secret `PROFILE_TOKEN`.

## Personalizzare

Tutti i testi stanno in `data/profile.json`: nome, tagline (3 righe), stack e la riga "now".
Dopo una modifica e un push, la Action rigenera le card in automatico.

Per un'anteprima in locale:

```bash
pip install -r requirements.txt
GITHUB_TOKEN=$(gh auth token) python scripts/fetch_data.py   # dati veri (opzionale)
python scripts/render_cards.py                               # card animate
STATIC=1 python scripts/render_cards.py                      # solo frame finale, per screenshot
```

Apri `cards/light/hero.svg` nel browser per vedere l'animazione.

## Come funziona

- `scripts/fetch_data.py`: legge da GraphQL il calendario dei contributi (ultimi 12 mesi) e
  le PR **mergiate in repo non tuoi**, che sono i tuoi contributi open source.
- `scripts/render_cards.py`: genera 5 SVG × 2 temi (light/dark). Font e CSS sono
  incorporati nei file, perché GitHub mostra le immagini dentro `<img>` e blocca le risorse esterne.
- Il README usa `<picture>` con `prefers-color-scheme`, così ogni visitatore vede il tema
  che usa su GitHub.
- Le animazioni si disattivano per chi ha impostato "riduci movimento" nel sistema operativo.
- Font: Space Grotesk e JetBrains Mono (licenza OFL, in `fonts/`).
