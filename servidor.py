# -*- coding: utf-8 -*-
"""
Sirve el Dashboard de Ventas de Grupo La Independiente en Railway, SOLO a quien
entre con usuario y clave. Biblioteca estandar de Python, sin dependencias.

Mismo esquema que las fichas tecnicas:

  - Pantalla de ingreso propia y boton "Salir" dentro del dashboard.
  - La sesion viaja en una galleta firmada con HMAC (nadie puede fabricarla),
    HttpOnly y SameSite. Se vence sola (HORAS_SESION, 12 por defecto).
  - La llave de la firma sale de las propias claves: cambiar la clave en
    Railway cierra cualquier sesion abierta.
  - Freno a los intentos a lo bruto: 12 fallos en 10 minutos bloquean esa IP.

USUARIOS: en Railway, pestana Variables. El NOMBRE de la variable es el usuario
y el valor es la clave:

    ADMIN_laindependiente = la-clave

Se pueden crear varios (ADMIN_otro = ...). El usuario no distingue mayusculas;
la clave si. SI NO HAY NINGUN USUARIO, NO SE ENTREGA NADA (responde 503): se
prefiere que la pagina no cargue a que ventas y costos queden abiertos.

Las claves NUNCA van en el repositorio.
"""

import base64
import hashlib
import hmac
import html
import os
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.abspath(__file__))
PUERTO = int(os.environ.get("PORT", "8080"))
GALLETA = "sesion_dashboard"
ARCHIVO = "index.html"

try:
    HORAS_SESION = max(1, int(os.environ.get("HORAS_SESION", "12")))
except ValueError:
    HORAS_SESION = 12


def leer_usuarios():
    usuarios = {}
    for nombre, valor in os.environ.items():
        if not nombre.upper().startswith("ADMIN_"):
            continue
        usuario, clave = nombre[6:], (valor or "").strip()
        if usuario and clave:
            usuarios[usuario.upper()] = {"clave": clave, "nombre": usuario}
    return usuarios


USUARIOS = leer_usuarios()


def comprobar(usuario, clave):
    u = (usuario or "").strip().upper().encode("utf-8")
    c = (clave or "").encode("utf-8")
    hallada = None
    for llave, perfil in USUARIOS.items():
        ok_u = hmac.compare_digest(u, llave.encode("utf-8"))
        ok_c = hmac.compare_digest(c, perfil["clave"].encode("utf-8"))
        if ok_u and ok_c:
            hallada = llave
    return hallada


def _secreto():
    material = "|".join(sorted(p["clave"] for p in USUARIOS.values()))
    return hashlib.sha256(("dashboard|" + material).encode("utf-8")).digest()


def firmar_sesion(llave):
    vence = int(time.time()) + HORAS_SESION * 3600
    cuerpo = f"{llave}|{vence}".encode("utf-8")
    firma = hmac.new(_secreto(), cuerpo, hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(cuerpo).decode("ascii").rstrip("=") + "." + firma


def leer_sesion(valor):
    if not valor or "." not in valor:
        return None
    crudo, _, firma = valor.rpartition(".")
    try:
        cuerpo = base64.urlsafe_b64decode(crudo + "=" * (-len(crudo) % 4))
    except Exception:
        return None
    esperada = hmac.new(_secreto(), cuerpo, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(firma, esperada):
        return None
    try:
        llave, _, vence = cuerpo.decode("utf-8").rpartition("|")
        if int(vence) < time.time():
            return None
    except Exception:
        return None
    return USUARIOS.get(llave)


_intentos = {}


def demasiados_intentos(ip):
    fallos = [t for t in _intentos.get(ip, []) if time.time() - t < 600]
    _intentos[ip] = fallos
    return len(fallos) >= 12


def anotar_fallo(ip):
    _intentos.setdefault(ip, []).append(time.time())
    if len(_intentos) > 500:
        for k in [k for k, v in _intentos.items() if not v or time.time() - v[-1] > 600]:
            _intentos.pop(k, None)


_ENTRAR = """<!doctype html>
<meta charset="utf-8">
<title>Dashboard de Ventas · Grupo La Independiente</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<style>
  :root{--fondo:#0d1117;--tarjeta:#161b22;--texto:#e6edf3;--tenue:#8b949e;--linea:#30363d;--acento:#e8394d;--error:#f08076;--bien:#4ea87a}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--fondo);
       color:var(--texto);padding:16px;font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  .caja{width:100%;max-width:380px;background:var(--tarjeta);border:1px solid var(--linea);border-radius:14px;padding:32px 28px}
  .marca{display:flex;align-items:center;gap:12px;margin-bottom:26px}
  .marca .ico{font-size:28px}
  .marca b{font-size:17px;display:block}
  .marca span{font-size:11px;color:var(--tenue);letter-spacing:.07em;text-transform:uppercase}
  label{display:block;font-size:12.5px;color:var(--tenue);margin:0 0 6px}
  input{width:100%;padding:11px 13px;margin-bottom:16px;font-size:16px;color:var(--texto);background:var(--fondo);
        border:1px solid var(--linea);border-radius:9px}
  input:focus{outline:2px solid var(--acento);outline-offset:-1px;border-color:transparent}
  button{width:100%;padding:12px;font-size:15px;font-weight:600;color:#fff;cursor:pointer;background:var(--acento);border:0;border-radius:9px}
  button:hover{filter:brightness(1.08)}
  .aviso{margin:0 0 18px;padding:10px 13px;border-radius:9px;font-size:13.5px;background:rgba(240,128,118,.12);color:var(--error)}
  .bien{background:rgba(78,168,122,.13);color:var(--bien)}
  .pie{margin:22px 0 0;font-size:12px;color:var(--tenue)}
</style>
<div class="caja">
  <div class="marca"><div class="ico">&#128202;</div>
    <div><b>Dashboard de Ventas</b><span>Grupo La Independiente</span></div></div>
  __AVISO__
  <form method="post" action="/entrar">
    <label for="u">Usuario</label>
    <input id="u" name="usuario" autocomplete="username" autocapitalize="none" autocorrect="off" spellcheck="false" required autofocus>
    <label for="c">Contrase&ntilde;a</label>
    <input id="c" name="clave" type="password" autocomplete="current-password" required>
    <button type="submit">Entrar</button>
  </form>
  <p class="pie">El usuario no distingue may&uacute;sculas; la contrase&ntilde;a s&iacute;. Si no la tienes, p&iacute;desela al &aacute;rea de costos.</p>
</div>
"""


def pantalla_entrar(aviso="", clase=""):
    html_aviso = f'<p class="aviso {clase}">{html.escape(aviso)}</p>' if aviso else ""
    return _ENTRAR.replace("__AVISO__", html_aviso).encode("utf-8")


def boton_salir(perfil):
    quien = html.escape(perfil["nombre"])
    return ("""
<script>
(function(){
  var h = document.querySelector(".header-right");
  if (!h) return;
  var a = document.createElement("a");
  a.href = "/salir";
  a.textContent = "Salir · __QUIEN__";
  a.title = "Cerrar la sesión";
  a.style.cssText = "font-size:.65rem;color:#8b949e;text-decoration:none;border:1px solid #30363d;border-radius:6px;padding:3px 9px;margin-top:4px;display:inline-block";
  h.appendChild(a);
})();
</script>
""").replace("__QUIEN__", quien).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "DashboardLI"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def _responder(self, codigo, cuerpo, tipo="text/plain; charset=utf-8", extra=None):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(cuerpo)

    def _galleta(self, valor, horas):
        partes = [f"{GALLETA}={valor}", "Path=/", "HttpOnly", "SameSite=Lax"]
        if self.headers.get("X-Forwarded-Proto", "").startswith("https"):
            partes.append("Secure")
        partes.append(f"Max-Age={int(horas * 3600)}")
        return "; ".join(partes)

    def _sesion(self):
        for trozo in self.headers.get("Cookie", "").split(";"):
            nombre, _, valor = trozo.strip().partition("=")
            if nombre == GALLETA:
                return leer_sesion(valor)
        return None

    def _sin_configurar(self):
        self._responder(503, (
            "Falta configurar el usuario del dashboard.\n\n"
            "En Railway, pestana Variables, crea una variable cuyo NOMBRE es\n"
            "ADMIN_<usuario> y cuyo VALOR es la clave. Ejemplo:\n\n"
            "    ADMIN_laindependiente = la clave\n\n"
            "Hasta entonces el dashboard no se entrega.\n").encode("utf-8"))

    def do_GET(self):
        if not USUARIOS:
            return self._sin_configurar()
        camino = urllib.parse.urlparse(self.path).path
        if camino == "/favicon.ico":
            return self._responder(404, b"")
        if camino == "/salir":
            return self._responder(200, pantalla_entrar("Saliste del dashboard.", "bien"),
                                   "text/html; charset=utf-8",
                                   {"Set-Cookie": self._galleta("", 0)})
        perfil = self._sesion()
        if not perfil:
            return self._responder(200, pantalla_entrar(), "text/html; charset=utf-8")
        with open(os.path.join(RAIZ, ARCHIVO), "rb") as fh:
            cuerpo = fh.read() + boton_salir(perfil)
        return self._responder(200, cuerpo, "text/html; charset=utf-8")

    do_HEAD = do_GET

    def do_POST(self):
        if not USUARIOS:
            return self._sin_configurar()
        if urllib.parse.urlparse(self.path).path != "/entrar":
            return self._responder(404, b"No existe.\n")
        ip = self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or self.address_string()
        if demasiados_intentos(ip):
            return self._responder(429, pantalla_entrar("Demasiados intentos fallidos. Espera unos minutos."),
                                   "text/html; charset=utf-8")
        try:
            largo = min(int(self.headers.get("Content-Length", "0")), 8192)
        except ValueError:
            largo = 0
        campos = urllib.parse.parse_qs(self.rfile.read(largo).decode("utf-8", "replace"))
        llave = comprobar((campos.get("usuario") or [""])[0], (campos.get("clave") or [""])[0])
        if not llave:
            anotar_fallo(ip)
            return self._responder(401, pantalla_entrar("Usuario o contraseña incorrectos."),
                                   "text/html; charset=utf-8")
        return self._responder(303, b"", extra={
            "Location": "/",
            "Set-Cookie": self._galleta(firmar_sesion(llave), HORAS_SESION)})

    def log_message(self, formato, *args):
        sys.stdout.write("%s - %s\n" % (self.address_string(), formato % args))
        sys.stdout.flush()


if __name__ == "__main__":
    if not USUARIOS:
        print("ATENCION: no hay ningun usuario ADMIN_<usuario>. El dashboard respondera 503.", flush=True)
    else:
        print("Usuarios configurados: " + ", ".join(p["nombre"] for p in USUARIOS.values()), flush=True)
    print(f"Dashboard en el puerto {PUERTO}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PUERTO), Handler).serve_forever()
