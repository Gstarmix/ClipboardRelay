from __future__ import annotations
import argparse
import io
import logging
import os
import socket
import sys
from pathlib import Path
from typing import Optional
from flask import Flask, jsonify, render_template, request
logger = logging.getLogger(__name__)
DEFAULT_PORT = 5681
DEFAULT_HOST = "0.0.0.0"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
APP_NAME = "Clipboard Relay"
MAX_VIDEO_BYTES = 500 * 1024 * 1024
MAX_AUDIO_BYTES = 1024 * 1024 * 1024
_SCRIPT_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = _SCRIPT_DIR / "_uploads"
PHOTOS_DIR = UPLOADS_DIR / "photos"
VIDEOS_DIR = UPLOADS_DIR / "videos"
AUDIOS_DIR = UPLOADS_DIR / "audios"
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_AUDIO_BYTES + (5 * 1024 * 1024)
def _copy_image_to_clipboard_windows(image_bytes: bytes, mime: str = "image/jpeg") -> tuple[bool, str]:
    try:
        from PIL import Image
    except ImportError:
        return (False, "Pillow indisponible (pip install Pillow)")
    try:
        import win32clipboard
        import win32con
    except ImportError:
        return (False, "pywin32 indisponible (pip install pywin32)")
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="BMP")
        bmp_data = out.getvalue()
        dib_data = bmp_data[14:]
    except Exception as e:
        return (False, f"Conversion image échouée : {e}")
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_DIB, dib_data)
        win32clipboard.CloseClipboard()
        return (True, "OK")
    except Exception as e:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        return (False, f"Écriture clipboard échouée : {e}")
_BEEP_ENABLED = False
def _notify_user(title: str, message: str) -> None:
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=4, threaded=True)
    except Exception as e:
        logger.debug("Toast indisponible : %s", e)
    if _BEEP_ENABLED:
        try:
            import winsound
            winsound.Beep(800, 150)
        except Exception:
            pass
@app.route("/", methods=["GET"])
def index():
    return render_template("mobile.html")
@app.route("/api/upload_photo", methods=["POST"])
def api_upload_photo():
    f = request.files.get("file") or request.files.get("photo")
    if f is None or not f.filename:
        return jsonify({"error": "champ 'file' manquant"}), 400
    img_bytes = f.read()
    if not img_bytes:
        return jsonify({"error": "fichier vide"}), 400
    if len(img_bytes) > MAX_IMAGE_BYTES:
        return jsonify({
            "error": "image trop grosse",
            "max_bytes": MAX_IMAGE_BYTES,
            "got_bytes": len(img_bytes),
        }), 400
    mime = f.mimetype or "image/jpeg"
    ok, reason = _copy_image_to_clipboard_windows(img_bytes, mime)
    if not ok:
        logger.error("Clipboard copy KO : %s", reason)
        return jsonify({"error": reason}), 500
    custom_name = request.form.get("custom_name") or request.args.get("custom_name")
    ext = _detect_ext_from_mime_or_filename(mime, f.filename, default="jpg")
    saved_path = _save_to_uploads_dir(PHOTOS_DIR, img_bytes, ext, custom_name=custom_name)
    if saved_path:
        logger.info("Photo sauvegardée : %s", saved_path)
    _notify_user(
        APP_NAME,
        f"📋 Photo reçue ({len(img_bytes) // 1024} kB) — Ctrl+V dans ton chat web",
    )
    logger.info("Photo copiée dans clipboard (%d bytes, mime=%s)", len(img_bytes), mime)
    return jsonify({
        "ok": True,
        "size_bytes": len(img_bytes),
        "mime": mime,
        "saved_path": saved_path,
    })
@app.route("/api/upload_video", methods=["POST"])
def api_upload_video():
    f = (request.files.get("file")
         or request.files.get("video")
         or request.files.get("attachment"))
    if f is None or not f.filename:
        return jsonify({"error": "champ 'file' manquant"}), 400
    raw = f.read()
    if not raw:
        return jsonify({"error": "fichier vide"}), 400
    if len(raw) > MAX_VIDEO_BYTES:
        return jsonify({
            "error": "vidéo trop grosse",
            "max_bytes": MAX_VIDEO_BYTES,
            "got_bytes": len(raw),
        }), 400
    mime = f.mimetype or "video/mp4"
    custom_name = request.form.get("custom_name") or request.args.get("custom_name")
    ext = _detect_ext_from_mime_or_filename(mime, f.filename, default="mp4")
    saved_path = _save_to_uploads_dir(VIDEOS_DIR, raw, ext, custom_name=custom_name)
    if not saved_path:
        return jsonify({"error": "écriture disque échouée"}), 500
    logger.info("Vidéo sauvegardée : %s (%d bytes, mime=%s)", saved_path, len(raw), mime)
    _notify_user(
        APP_NAME,
        f"🎥 Vidéo reçue ({len(raw) // (1024*1024)} MB) — enregistrée dans _uploads/videos/",
    )
    return jsonify({
        "ok": True,
        "size_bytes": len(raw),
        "mime": mime,
        "saved_path": saved_path,
    })
@app.route("/api/upload_audio", methods=["POST"])
def api_upload_audio():
    f = (request.files.get("file")
         or request.files.get("audio")
         or request.files.get("attachment"))
    if f is None or not f.filename:
        return jsonify({"error": "champ 'file' manquant"}), 400
    raw = f.read()
    if not raw:
        return jsonify({"error": "fichier vide"}), 400
    if len(raw) > MAX_AUDIO_BYTES:
        return jsonify({
            "error": "audio trop gros",
            "max_bytes": MAX_AUDIO_BYTES,
            "got_bytes": len(raw),
        }), 400
    mime = f.mimetype or "audio/webm"
    custom_name = request.form.get("custom_name") or request.args.get("custom_name")
    ext = _detect_ext_from_mime_or_filename(mime, f.filename, default="webm")
    saved_path = _save_to_uploads_dir(AUDIOS_DIR, raw, ext, custom_name=custom_name)
    if not saved_path:
        return jsonify({"error": "écriture disque échouée"}), 500
    logger.info("Audio sauvegardé : %s (%d bytes, mime=%s)", saved_path, len(raw), mime)
    _notify_user(
        APP_NAME,
        f"🎤 Audio reçu ({len(raw) // 1024} kB) — enregistré dans _uploads/audios/",
    )
    return jsonify({
        "ok": True,
        "size_bytes": len(raw),
        "mime": mime,
        "saved_path": saved_path,
    })
@app.route("/api/health", methods=["GET"])
def api_health():
    deps = {}
    try:
        import PIL
        deps["Pillow"] = True
    except ImportError:
        deps["Pillow"] = False
    try:
        import win32clipboard
        deps["pywin32"] = True
    except ImportError:
        deps["pywin32"] = False
    try:
        import win10toast
        deps["win10toast"] = True
    except ImportError:
        deps["win10toast"] = False
    return jsonify({
        "ok": True,
        "service": APP_NAME,
        "version": "0.1",
        "deps": deps,
        "clipboard_ready": deps["Pillow"] and deps["pywin32"],
    })
def _get_lan_ip() -> Optional[str]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None
def _get_tailscale_ip() -> Optional[str]:
    import subprocess
    try:
        out = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True, text=True, timeout=2,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip().splitlines()[0]
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None
def _setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
_TRAY_PORT = DEFAULT_PORT
def _create_tray_icon():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (64, 64), color=(126, 182, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([14, 18, 50, 56], fill=(255, 255, 255), outline=(40, 40, 40), width=2)
    draw.rectangle([24, 10, 40, 22], fill=(220, 220, 220), outline=(40, 40, 40), width=2)
    for y in (28, 36, 44):
        draw.rectangle([20, y, 44, y + 2], fill=(126, 182, 255))
    return img
def _open_url(url: str) -> None:
    import webbrowser
    try:
        webbrowser.open(url, new=2)
    except Exception as e:
        logger.debug("Open URL %s a échoué : %s", url, e)
def _open_folder(folder: Path) -> None:
    import subprocess as _sp
    try:
        folder.mkdir(parents=True, exist_ok=True)
        _sp.Popen(["explorer.exe", str(folder)])
    except Exception as e:
        logger.warning("Open folder %s a échoué : %s", folder, e)
def _open_photos_folder() -> None:
    _open_folder(PHOTOS_DIR)
def _open_videos_folder() -> None:
    _open_folder(VIDEOS_DIR)
def _open_audios_folder() -> None:
    _open_folder(AUDIOS_DIR)
def _open_log() -> None:
    import os as _os
    import subprocess as _sp
    log_path = _os.path.join(_os.environ.get("TEMP", "."), "Clipboard_Relay.log")
    if _os.path.isfile(log_path):
        try:
            _sp.Popen(["notepad.exe", log_path])
        except Exception as e:
            logger.warning("Open log a échoué : %s", e)
    else:
        logger.info("Pas de log à %s (mode console actif)", log_path)
def _quit_relay(icon, _item=None):
    try:
        icon.stop()
    except Exception:
        pass
    import os as _os
    _os._exit(0)
def _run_tray_thread(port: int, lan_ip: Optional[str], ts_ip: Optional[str]) -> None:
    try:
        import pystray
    except ImportError:
        logger.warning(
            "pystray indisponible — pas d'icône tray. "
            "Installe via : pip install pystray"
        )
        return
    image = _create_tray_icon()
    base_url = f"http://127.0.0.1:{port}/"
    health_url = f"http://127.0.0.1:{port}/api/health"
    menu_items = [
        pystray.MenuItem(
            f"📋 Clipboard Relay · port {port}",
            None,
            enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "🌐 Ouvrir page mobile (localhost)",
            lambda icon, item: _open_url(base_url),
        ),
    ]
    if lan_ip:
        menu_items.append(pystray.MenuItem(
            f"📶 Wi-Fi local : {lan_ip}:{port}",
            lambda icon, item: _open_url(f"http://{lan_ip}:{port}/"),
        ))
    if ts_ip:
        menu_items.append(pystray.MenuItem(
            f"🔒 Tailscale : {ts_ip}:{port}",
            lambda icon, item: _open_url(f"http://{ts_ip}:{port}/"),
        ))
    menu_items.extend([
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🩺 Status (santé / deps)", lambda icon, item: _open_url(health_url)),
        pystray.MenuItem("📁 Photos", lambda icon, item: _open_photos_folder()),
        pystray.MenuItem("🎥 Vidéos", lambda icon, item: _open_videos_folder()),
        pystray.MenuItem("🎤 Audios", lambda icon, item: _open_audios_folder()),
        pystray.MenuItem("📄 Voir le log", lambda icon, item: _open_log()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ Quitter", _quit_relay),
    ])
    icon = pystray.Icon(
        "clipboard_relay",
        image,
        title=f"Clipboard Relay · port {port}",
        menu=pystray.Menu(*menu_items),
    )
    icon.run()
def _sanitize_custom_name(raw: Optional[str]) -> str:
    if not raw:
        return ""
    import re as _re_san
    s = raw.strip().replace(" ", "_")
    s = _re_san.sub(r"[^A-Za-z0-9_.-]", "", s)
    s = s.strip("._-")
    return s[:60]
def _save_to_uploads_dir(
    folder: Path,
    raw_bytes: bytes,
    ext: str,
    custom_name: Optional[str] = None,
) -> Optional[str]:
    try:
        from datetime import datetime
        folder.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        custom_san = _sanitize_custom_name(custom_name)
        suffix_part = f"_{custom_san}" if custom_san else ""
        ext_clean = ext.lstrip(".").lower()[:5] or "bin"
        base_name = f"{ts}{suffix_part}.{ext_clean}"
        out_path = folder / base_name
        n = 1
        while out_path.exists():
            n += 1
            out_path = folder / f"{ts}{suffix_part}_{n}.{ext_clean}"
        out_path.write_bytes(raw_bytes)
        return str(out_path)
    except Exception as e:
        logger.warning("Sauvegarde disque a échoué (%s) : %s", folder, e)
        return None
def _detect_ext_from_mime_or_filename(mime: str, filename: Optional[str], default: str) -> str:
    mime_map = {
        "image/jpeg": "jpg", "image/png": "png", "image/gif": "gif",
        "image/webp": "webp", "image/heic": "heic",
        "video/mp4": "mp4", "video/quicktime": "mov",
        "video/webm": "webm", "video/x-msvideo": "avi",
        "audio/webm": "webm", "audio/mpeg": "mp3",
        "audio/mp4": "m4a", "audio/x-m4a": "m4a",
        "audio/ogg": "ogg", "audio/wav": "wav", "audio/x-wav": "wav",
    }
    ext = mime_map.get(mime)
    if ext:
        return ext
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()[:5]
        if ext:
            return ext
    return default
def _force_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
def main() -> int:
    _force_utf8_stdio()
    p = argparse.ArgumentParser(description=APP_NAME + " v0.1")
    p.add_argument("--port", type=int, default=DEFAULT_PORT,
                   help=f"Port d'écoute (défaut {DEFAULT_PORT})")
    p.add_argument("--host", default=DEFAULT_HOST,
                   help=f"Host (défaut {DEFAULT_HOST} = toutes interfaces)")
    p.add_argument("--debug", action="store_true",
                   help="Active le mode debug Flask + logs DEBUG")
    p.add_argument("--no-tray", action="store_true",
                   help="Désactive l'icône system tray (Phase v0.1.4)")
    p.add_argument("--beep", action="store_true",
                   help="Active le bip système à chaque photo reçue "
                        "(Phase v0.1.5 — désactivé par défaut, gênant à répétition)")
    args = p.parse_args()
    global _TRAY_PORT, _BEEP_ENABLED
    _TRAY_PORT = args.port
    _BEEP_ENABLED = bool(args.beep)
    _setup_logging(debug=args.debug)
    try:
        import PIL
    except ImportError:
        print("❌ Pillow indisponible. Installe : pip install -r requirements.txt", file=sys.stderr)
        return 1
    try:
        import win32clipboard
    except ImportError:
        if os.name == "nt":
            print("❌ pywin32 indisponible (Windows). Installe : pip install -r requirements.txt", file=sys.stderr)
            return 1
        print("⚠ pywin32 indisponible (non-Windows). Le clipboard ne marchera pas, mais le serveur tourne.", file=sys.stderr)
    lan_ip = _get_lan_ip()
    ts_ip = _get_tailscale_ip()
    print(f"\n🚀 {APP_NAME} v0.1 — port {args.port}")
    print("Accès depuis le téléphone :")
    if lan_ip:
        print(f"  • Wi-Fi local  : http://{lan_ip}:{args.port}/")
    if ts_ip:
        print(f"  • Tailscale    : http://{ts_ip}:{args.port}/")
    print(f"  • Localhost    : http://127.0.0.1:{args.port}/  (PC uniquement)")
    print("\nWorkflow :")
    print("  1. Sur ton tel → ouvre l'URL → 📷 Prendre une photo")
    print("  2. Ctrl+V dans ton chat web (Claude.ai / AI Studio / Gemini / ChatGPT)")
    print("\nCtrl+C pour arrêter.\n")
    if not args.no_tray:
        import threading as _threading
        tray_thread = _threading.Thread(
            target=_run_tray_thread,
            args=(args.port, lan_ip, ts_ip),
            daemon=True,
            name="clipboard-relay-tray",
        )
        tray_thread.start()
        urls_summary = []
        if ts_ip:
            urls_summary.append(f"Tailscale {ts_ip}:{args.port}")
        if lan_ip:
            urls_summary.append(f"WiFi {lan_ip}:{args.port}")
        urls_summary.append(f"localhost {args.port}")
        _notify_user(
            f"{APP_NAME} actif",
            "Click droit sur l'icône 📋 du tray pour les options. "
            + "URLs : " + " · ".join(urls_summary),
        )
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
    return 0
if __name__ == "__main__":
    sys.exit(main())