# 📋 Clipboard Relay

Service local qui relaye photos / vidéos / audios depuis ton téléphone vers ton PC. Selon le type de média :
- **Photo** : copiée dans le **presse-papier Windows** pour `Ctrl+V` direct dans un chat web (Claude.ai, AI Studio Gemini, Gemini web, ChatGPT…) **+ sauvegardée** dans `_uploads/photos/`.
- **Vidéo** : sauvegardée dans `_uploads/videos/` (pas de Ctrl+V — les chats web n'acceptent pas le paste de vidéo).
- **Audio** : sauvegardée dans `_uploads/audios/` (idem). MediaRecorder direct ou import d'un fichier audio existant (cours longs 3h+ depuis une app dictaphone).

> **Statut** : v0.1.6 · **Plateforme** : Windows (Linux/macOS = clipboard non implémenté pour le moment) · **Auteur** : Gaylord (Gstar) en collaboration avec Claude Code, mai 2026.

---

## Pourquoi cet outil

Le projet sœur **Compagnon_Revision** consomme du quota Pro Max Claude (ou des tokens API) à chaque photo envoyée pour révision. Pour les sessions où tu veux **économiser le quota** ou tester la même question dans plusieurs LLM gratuits / web, ce relay te permet de :

1. Prendre la photo depuis ton tel
2. Coller (`Ctrl+V`) dans le chat web ouvert sur ton PC

Pas d'API à gérer, pas d'auth de chat web à automatiser (donc **0 risque de ban ToS**), pas de DOM manipulation fragile. Juste un presse-papier qui voyage du tel au PC.

Depuis **v0.1.6**, l'outil ne gère plus seulement les photos : tu peux aussi relayer des **vidéos** (filmées ou importées) et des **enregistrements audio** (MediaRecorder ou import) — sans les copier dans le presse-papier (les chats web ne les acceptent pas en paste), juste sauvegardés sur le PC dans `_uploads/{videos,audios}/` pour récupération.

## Récap des 3 modes (v0.1.6)

| Mode | Comportement PC | Sauvegarde | Cap | Format natif |
|---|---|---|---|---|
| 📷 **Photo** | Copie clipboard Windows → `Ctrl+V` chat web | `_uploads/photos/` | 20 MB | JPEG / PNG / WebP / HEIC |
| 🎥 **Vidéo** | Pas de clipboard, juste sauvegarde + notif | `_uploads/videos/` | 500 MB | MP4 (Android) / MOV (iOS) |
| 🎤 **Audio** | Pas de clipboard, juste sauvegarde + notif | `_uploads/audios/` | 1 GB | WebM/Opus (Android) / M4A (iOS) |

**Nom des fichiers** : `YYYY-MM-DD_HHMMSS.ext` par défaut, ou `YYYY-MM-DD_HHMMSS_<nom-perso>.ext` si tu remplis le champ « 📝 Nom personnalisé » sur la page mobile (sanitized côté serveur : alphanumériques + tirets + underscores + points). Suffixe `_N` automatique en cas de collision dans la même seconde (multi-shoot rapide).

**Pour les enregistrements audio longs (cours 3h+)** : recommandation = utiliser une app dictaphone système (Voice Memos iOS, Dictaphone Android, etc.) puis cliquer **📁 Importer un audio existant** sur la page mobile. L'enregistrement direct via MediaRecorder navigateur exige que l'écran reste allumé tout du long, ce qui est inconfortable au-delà de ~1h. L'import accepte n'importe quel format audio (mp3, m4a, ogg, wav…).

---

## Installation

```powershell
# Depuis le dossier Clipboard_Relay/
python -m pip install -r requirements.txt
```

Dépendances :
- **Flask** : serveur HTTP
- **Pillow** : conversion JPEG/PNG → DIB pour le clipboard Windows
- **pywin32** : accès `win32clipboard.SetClipboardData(CF_DIB, ...)`
- **win10toast** : notification toast (optionnel — fallback bip système si absent)

---

## Lancement

### Mode console (debug)

```powershell
python relay.py
```

Affiche au boot les URLs accessibles depuis ton tel :

```
🚀 Clipboard Relay v0.1 — port 5681
Accès depuis le téléphone :
  • Wi-Fi local  : http://192.168.1.42:5681/
  • Tailscale    : http://100.x.x.x:5681/
  • Localhost    : http://127.0.0.1:5681/  (PC uniquement)
```

### Mode silencieux (recommandé)

Double-clic sur **`start_relay.vbs`** → lance `pythonw.exe relay.py` en background sans console. Pour démarrer auto au boot Windows, copie ce `.vbs` dans :

```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
```

Pour arrêter : Gestionnaire de tâches → tuer le `pythonw.exe` qui tourne `relay.py`.

---

## Workflow (Phase v0.1.5)

1. **PC** : `start_relay.vbs` (background, écoute port 5681)
   - Une **icône 📋 apparaît dans le system tray** (zone notification Windows, à côté de l'horloge). Click droit → menu : ouvrir page mobile / status / **ouvrir dossier photos** / log / quitter.
   - Une **notification toast** apparaît au démarrage avec les URLs disponibles.
2. **Téléphone** : ouvre une des URLs affichées au boot (Wi-Fi LAN ou Tailscale)
3. Tu vois le bouton **📷 Prendre une photo** → click → app caméra système
4. **Preview avec recadrage et rotation** :
   - Glisser sur l'image pour redessiner la zone de recadrage (Cropper.js v1.6.2)
   - Boutons **↺ 90°** / **↻ 90°** pour pivoter (utile si photo prise de travers)
   - **↩ Reset** pour annuler le crop
   - **📷 Autre photo** pour reprendre
5. Click **✂ Envoyer au PC** → upload (~1-2s)
6. **Sur PC** : notification toast Windows (sans bip par défaut, opt-in via `--beep`). La photo est aussi **sauvegardée dans `_uploads/photos/`** (sous-dossier du projet, format `YYYY-MM-DD_HHMMSS.jpg`)
7. **`Ctrl+V`** dans ton chat web (Claude.ai, AI Studio, Gemini, ChatGPT…) → photo collée

Tu peux enchaîner autant de photos que tu veux. Le presse-papier est écrasé à chaque nouveau Ctrl+V (donc colle toujours la dernière), mais le dossier `_uploads/photos/` les garde toutes pour récupération ultérieure (drag-drop manuel, archivage).

### Bip système (opt-in v0.1.5)

Avant v0.1.5, chaque photo déclenchait un `winsound.Beep`. C'était gênant à répétition (multi-shoot, sessions longues). Désactivé par défaut. Pour le réactiver : lance avec `python relay.py --beep`.

---

## Sécurité

⚠ **Ne PAS exposer ce service en Funnel Tailscale public** sans ajouter une auth Basic. Le service écrit directement dans le presse-papier Windows : n'importe qui qui peut accéder à l'URL peut polluer ton presse-papier.

Garde-le en :
- **LAN local** (`http://192.168.x.x:5681/`) : accessible uniquement depuis le même Wi-Fi
- **Tailnet privé** (`http://100.x.x.x:5681/`) : accessible depuis tes appareils Tailscale uniquement

### Quand utiliser Tailscale ?

**Obligatoire** si :
- Tu es **chez toi mais le tel et le PC ne sont PAS sur le même Wi-Fi** (ex: PC sur Wi-Fi 5GHz, tel sur 2.4GHz isolé ; PC sur Ethernet et tel sur Wi-Fi guest ; etc.)
- Tu es **en déplacement** (fac, café, train) et le tel est en 4G/5G ou sur un Wi-Fi public

**Pas nécessaire** si tu es sur le même Wi-Fi (l'IP LAN `192.168.x.x` ou `10.x.x.x` marche directement).

**Install Tailscale en 2 minutes** :
1. PC : [Télécharge Tailscale Windows](https://tailscale.com/download/windows), install, login (Google / GitHub / email).
2. Téléphone : install l'app Tailscale ([App Store](https://apps.apple.com/app/tailscale/id1470499037) / [Play Store](https://play.google.com/store/apps/details?id=com.tailscale.ipn)), même login.
3. Les 2 appareils apparaissent dans ton tailnet avec une IP `100.x.x.x`. Le tel peut accéder à `http://100.x.x.x:5681/` (l'IP de ton PC) **n'importe où**.

Tailscale est gratuit jusqu'à 100 appareils. Pas de config, pas de reverse-proxy à monter, pas de port à ouvrir — c'est du peer-to-peer chiffré WireGuard.

Aucune auth implémentée en v0.1. Pour Funnel public, il faudrait ajouter un middleware `@before_request` qui check Basic Auth (pattern dispo dans `Compagnon_Revision/_scripts/web/app.py`).

---

## Endpoints

| Méthode | Path | Rôle |
|---|---|---|
| GET | `/` | Page mobile (UI 3 modes : photo / vidéo / audio) |
| POST | `/api/upload_photo` | Multipart `file` (+ optional `custom_name`) → copie clipboard Windows + sauve `_uploads/photos/` + notif |
| POST | `/api/upload_video` | **Phase v0.1.6** · Multipart `file` (+ optional `custom_name`) → sauve `_uploads/videos/` + notif. Pas de clipboard. Cap 500 MB. |
| POST | `/api/upload_audio` | **Phase v0.1.6** · Multipart `file` (+ optional `custom_name`) → sauve `_uploads/audios/` + notif. Pas de clipboard. Cap 1 GB. |
| GET | `/api/health` | Status + détection des dépendances installées |

`/api/health` example response :

```json
{
  "ok": true,
  "service": "Clipboard Relay",
  "version": "0.1",
  "deps": {
    "Pillow": true,
    "pywin32": true,
    "win10toast": true
  },
  "clipboard_ready": true
}
```

---

## Troubleshooting

### Le bouton « Prendre une photo » ouvre la galerie au lieu de la caméra

iOS Safari < 14.5 ignore parfois `capture="environment"`. Fix : tape la photo en plein écran depuis l'app **Safari** (pas Chrome iOS), iOS 17+ recommandé.

### `Ctrl+V` colle un fichier au lieu d'une image

Certains chats web (rares) attendent un upload via leur bouton dédié plutôt qu'un paste. Test dans Claude.ai d'abord (qui accepte les pastes d'image) avant de râler.

### Notification toast n'apparaît pas

`win10toast` est optionnel. Si non installé, juste le bip système retentit. Vérifie aussi tes paramètres « Notifications et actions » Windows (les toasts peuvent être désactivés globalement).

### `pythonw.exe` n'est pas trouvé par le `.vbs`

Vérifie que Python est dans le PATH système. `where python` et `where pythonw` doivent renvoyer un chemin. Sinon, édite `start_relay.vbs` pour mettre le chemin complet (`"C:\Python312\pythonw.exe"`).

### Le bouton 🎤 Enregistrer audio est grisé / dit « micro indisponible » (Phase v0.1.7)

Cause : `navigator.mediaDevices.getUserMedia` est `undefined` sur les origines HTTP côté mobile (sauf `localhost`). C'est une **restriction de sécurité du navigateur**, pas une question de permission Android — tes permissions Chrome (Microphone autorisé) n'ont pas d'effet ici.

**3 solutions** du plus simple au plus complet :

#### A — Importer audio depuis ton app dictaphone (recommandé)

Enregistre avec **n'importe quelle app dictaphone Android** (Voice Recorder, Dictaphone, Samsung Recorder, etc.) — elles ont un accès natif au micro système, marchent même hors-ligne, et supportent les enregistrements de plusieurs heures sans crash. Puis sur la page Clipboard_Relay du tel, click **📁 Importer un audio existant**, sélectionne le fichier. Marche immédiatement, supporte les cours 3h+, format mp3/m4a/ogg/wav accepté.

C'était de toute façon la recommandation pour les longs enregistrements (cf. section workflow).

#### B — Activer le flag Chrome « insecure origins as secure » (quick fix)

Sur ton tel Chrome :
1. Va à `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
2. Active le flag, ajoute `http://100.x.y.z:5681` (remplace par ton IP Tailscale du PC) dans la liste
3. Relance Chrome (force stop + ouvrir)

Le navigateur considérera désormais cette origine comme HTTPS pour les APIs sécurisées (getUserMedia, etc.). **Risque** : appliqué à TOUTES les APIs sécurisées de cette origine (geolocation, etc.). Acceptable vu que c'est ton propre service local sur tailnet privé, mais pas l'idéal côté hygiène.

#### C — Servir Clipboard_Relay en HTTPS via Tailscale serve

Tailscale fournit gratuitement un certificat TLS valide sur `*.ts.net`. Le port 443 est probablement déjà occupé sur ton PC (Compagnon). Utilise un autre port HTTPS supporté par Tailscale (8443) :

```powershell
tailscale serve --bg --https=8443 http://localhost:5681
```

L'URL devient `https://gstarmix.tailnet-name.ts.net:8443/` — TLS valide, getUserMedia marche immédiatement. Pour annuler : `tailscale serve --https=8443 off`.

Plus propre que B, mais demande de retenir l'URL avec `:8443`. Tu peux la bookmark sur ton tel.

### `start_relay.vbs` ouvre 1s puis disparaît silencieusement (Phase v0.1.1)

Le service crashe au boot mais la fenêtre `pythonw.exe` n'a pas de console donc tu ne vois rien. **Deux options** :

1. **Lance `start_relay_debug.bat`** à la place — console visible avec le traceback complet. Tu sauras exactement ce qui plante (typiquement `ImportError: No module named 'pywin32'` si l'install n'a pas pris).
2. **Ouvre `%TEMP%\Clipboard_Relay.log`** — depuis v0.1.1, le `.vbs` redirige stdout/stderr vers ce fichier. Tu y trouves le traceback Python complet.

Causes les plus fréquentes :
- `pywin32` pas installé dans le bon environnement Python : `python -m pip install pywin32` (pas `pip install` qui peut viser un autre Python si tu en as plusieurs)
- Port 5681 déjà occupé par autre chose : passe sur un autre port, `python relay.py --port 5682`
- `win10toast` crashe à l'init sur Python 3.12+ (lib pas maintenue) : depuis v0.1.1, le toast est totalement optionnel, tout exception est swallow → ne devrait plus bloquer le serveur.

Une fois la cause identifiée et fixée via `start_relay_debug.bat`, tu peux re-utiliser `start_relay.vbs` pour usage normal silencieux.

### Le presse-papier reste vide après upload

- Vérifie `/api/health` → `clipboard_ready: true`
- Si `pywin32: false`, installe : `pip install pywin32`
- Si `clipboard_ready: true` mais Ctrl+V ne marche pas dans le chat web, regarde la console (en mode debug `python relay.py --debug`) pour voir si le call `SetClipboardData` a échoué (clipboard verrouillé par une autre app temporairement → réessaye)

---

## Roadmap (si jamais)

- **v0.2** : auth Basic optionnelle pour exposer en Funnel public
- **v0.3** : support Linux (xclip / wl-copy) et macOS (pbcopy)
- **v0.4** : option pour copier aussi le texte (plus juste les images) — utile pour piper du LaTeX, du code, des liens
- **v1.0** : packaging en `.exe` autonome avec `pyinstaller` pour distribution sans dépendre de Python installé