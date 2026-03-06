import re
import sys
import io
import math
import os
import json
import threading
import time as _time_module
import sqlite3 as _sqlite3

os.environ["PYTHONUNBUFFERED"] = "1"

# ── HTTP server (stdlib pura, sin Flask) ──────────────────────────────────────
from http.server  import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote

# ── Seguridad de passwords (werkzeug, ya instalado con Flask) ─────────────────
try:
    from werkzeug.security import generate_password_hash, check_password_hash
    HAS_WERKZEUG = True
except ImportError:
    HAS_WERKZEUG = False
    def generate_password_hash(p): return p
    def check_password_hash(h, p): return h == p

# ── MySQL (opcional) ──────────────────────────────────────────────────────────
try:
    from mysql.connector import connect as mysql_connect, Error as MySQLError
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL  = False
    MySQLError = Exception

# ── UTF-8 stdout (Windows-safe) ───────────────────────────────────────────────
try:
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)


# ==============================================================================
#  TIPOS NATIVOS
# ==============================================================================

class IridiumObject(dict):
    """Dict accesible como objeto: obj.campo"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    def __repr__(self):
        return f"IridiumObject({dict.__repr__(self)})"


class IridiumMath:
    sqrt  = staticmethod(math.sqrt)
    pow   = staticmethod(math.pow)
    floor = staticmethod(math.floor)
    ceil  = staticmethod(math.ceil)
    abs   = staticmethod(abs)
    pi    = math.pi


class IridiumIA:
    def predict(self, data, mod):
        return f"Tensor({data}) procesado por {mod}"


# ==============================================================================
#  RESPUESTA HTTP NATIVA  ── usada por jsonify() y html()
# ==============================================================================

class IridiumResponse:
    def __init__(self, body, status=200, content_type="application/json"):
        self.body         = body
        self.status       = status
        self.content_type = content_type


def jsonify(data, status=200):
    """
    Convierte dict/lista a respuesta JSON.  Disponible global en .iri.

    Uso .iri:
        return jsonify({"ok": true, "nombre": nombre})
        return jsonify({"error": "No encontrado"}, 404)
    """
    return IridiumResponse(
        body         = json.dumps(data, ensure_ascii=False, default=str),
        status       = status,
        content_type = "application/json",
    )


def html(content, status=200):
    """Retorna HTML desde una ruta."""
    return IridiumResponse(content, status, "text/html; charset=utf-8")


# ==============================================================================
#  BASE DE DATOS NATIVA  ── objeto "db" disponible en .iri
# ==============================================================================

class IridiumDB:
    """
    Base de datos unificada — MySQL y SQLite.
    MySQL:  db.config("localhost", "root", "", "mi_base")
    SQLite: db.sqlite("archivo.db")
    Mismas funciones para ambos: db.query / db.query_one / db.exec
    """
    def __init__(self):
        self._cfg  = None
        self._conn = None
        self._modo = None
        self._path = None

    def config(self, host, user, password, database):
        self._cfg  = {"host": host, "user": user, "password": password, "database": database}
        self._conn = None
        self._modo = "mysql"
        print(f"🗄️  [DB] MySQL → {user}@{host}/{database}", flush=True)

    def sqlite(self, path="database.db"):
        self._path = path
        self._modo = "sqlite"
        self._conn = None
        print(f"🗄️  [DB] SQLite → {path}", flush=True)

    def _get_conn(self):
        if self._modo == "sqlite":
            if not self._conn:
                self._conn = _sqlite3.connect(self._path, check_same_thread=False)
                self._conn.row_factory = _sqlite3.Row
            return self._conn
        if not HAS_MYSQL:
            raise RuntimeError("[DB] Instalá mysql-connector-python")
        if not self._cfg:
            raise RuntimeError("[DB] Llamá db.config() o db.sqlite() primero.")
        try:
            if self._conn and self._conn.is_connected():
                return self._conn
        except Exception:
            pass
        self._conn = mysql_connect(**self._cfg)
        return self._conn

    def query(self, sql, *params):
        conn = self._get_conn()
        if self._modo == "sqlite":
            cur = conn.cursor()
            cur.execute(sql, params or ())
            return [IridiumObject(dict(r)) for r in cur.fetchall()]
        cur = conn.cursor(dictionary=True)
        cur.execute(sql.replace("?", "%s"), params or ())
        rows = cur.fetchall()
        cur.close()
        return [IridiumObject(r) for r in rows]

    def query_one(self, sql, *params):
        rows = self.query(sql, *params)
        return rows[0] if rows else IridiumObject({"_empty": True})

    def exec(self, sql, *params):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            if self._modo == "sqlite":
                cur.execute(sql, params or ())
            else:
                cur.execute(sql.replace("?", "%s"), params or ())
            conn.commit()
            return IridiumObject({"ok": True, "affected": cur.rowcount, "last_id": cur.lastrowid})
        except Exception as e:
            try: conn.rollback()
            except: pass
            return IridiumObject({"ok": False, "error": str(e)})

    def create_table(self, sql):
        conn = self._get_conn()
        conn.cursor().execute(sql)
        conn.commit()
        print("   📋 Tabla lista.", flush=True)

    def init(self):
        if self._modo == "sqlite":
            print("ℹ️  db.init() es solo para MySQL. Usá db.create_table()", flush=True); return
        if not HAS_MYSQL or not self._cfg:
            print("[DB] Configurá MySQL primero.", flush=True); return
        db_name = self._cfg["database"]
        cfg2 = {k: v for k, v in self._cfg.items() if k != "database"}
        cfg2["connection_timeout"] = 10
        try:
            conn = mysql_connect(**cfg2)
            cur  = conn.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cur.execute(f"USE `{db_name}`")
            print(f"✅ [DB] Base de datos '{db_name}' lista.", flush=True)
            tablas = [
                ("usuarios", """CREATE TABLE IF NOT EXISTS usuarios (id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(50) UNIQUE NOT NULL, email VARCHAR(100) UNIQUE NOT NULL, password VARCHAR(255) NOT NULL, exp INT DEFAULT 0, exp_semanal INT DEFAULT 0, gemas INT DEFAULT 100, racha INT DEFAULT 0, foto VARCHAR(255) DEFAULT 'default.png', fecha_borrado DATETIME DEFAULT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""),
                ("progreso_lecciones", """CREATE TABLE IF NOT EXISTS progreso_lecciones (id INT AUTO_INCREMENT PRIMARY KEY, usuario_nombre VARCHAR(50) NOT NULL, leccion_id VARCHAR(100) NOT NULL, completado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY unico_progreso (usuario_nombre, leccion_id), FOREIGN KEY (usuario_nombre) REFERENCES usuarios(nombre) ON DELETE CASCADE)"""),
                ("amigos", """CREATE TABLE IF NOT EXISTS amigos (id INT AUTO_INCREMENT PRIMARY KEY, usuario_envia VARCHAR(50) NOT NULL, usuario_recibe VARCHAR(50) NOT NULL, estado ENUM('pendiente','aceptado') DEFAULT 'pendiente', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY unico_amistad (usuario_envia, usuario_recibe))"""),
                ("notificaciones", """CREATE TABLE IF NOT EXISTS notificaciones (id INT AUTO_INCREMENT PRIMARY KEY, usuario_recibe VARCHAR(50) NOT NULL, titulo VARCHAR(100) NOT NULL, mensaje TEXT, tipo VARCHAR(50) DEFAULT 'general', leida TINYINT DEFAULT 0, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""),
                ("inventario_usuarios", """CREATE TABLE IF NOT EXISTS inventario_usuarios (id INT AUTO_INCREMENT PRIMARY KEY, usuario_nombre VARCHAR(50) NOT NULL, item_id VARCHAR(100) NOT NULL, obtenido_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY unico_item (usuario_nombre, item_id))"""),
                ("historial_liga", """CREATE TABLE IF NOT EXISTS historial_liga (id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(50) NOT NULL, exp_semanal INT DEFAULT 0, semana_anio VARCHAR(10) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""),
            ]
            for nombre_tabla, sql in tablas:
                cur.execute(sql)
                print(f"   📋 Tabla '{nombre_tabla}' lista.", flush=True)
            conn.commit(); cur.close(); conn.close()
            print("✅ [DB] Todas las tablas listas.", flush=True)
        except Exception as e:
            print(f"❌ [DB] Error: {e}", flush=True)

    def close(self):
        if self._conn:
            try: self._conn.close()
            except: pass
            self._conn = None

# ==============================================================================
#  ROUTER NATIVO
# ==============================================================================

class IridiumRouter:
    def __init__(self):
        self._routes = {}   # { (path, METHOD): handler }

    def add(self, path, methods, handler):
        for m in methods:
            self._routes[(path, m.upper())] = handler
            print(f"📌 [Route] {m.upper():7} {path}", flush=True)

    def dispatch(self, path, method, body, params, path_params):
        method = method.upper()
        # Exacto
        if (path, method) in self._routes:
            return self._routes[(path, method)](body, params, path_params)
        # Con parámetros de path  /ruta/<id>
        for (rp, rm), handler in self._routes.items():
            if rm != method: continue
            ok, extracted = self._match(rp, path)
            if ok:
                return handler(body, params, {**path_params, **extracted})
        return IridiumResponse(json.dumps({"error": f"Ruta no encontrada: {method} {path}"}), 404)

    @staticmethod
    def _match(template, actual):
        tp = template.strip("/").split("/")
        ap = actual.strip("/").split("/")
        if len(tp) != len(ap): return False, {}
        out = {}
        for t, a in zip(tp, ap):
            if t.startswith("<") and t.endswith(">"):
                out[t[1:-1]] = unquote(a)
            elif t != a:
                return False, {}
        return True, out


# ==============================================================================
#  CLASES DEFINIDAS EN .iri
# ==============================================================================

class IridiumClass:
    """
    Clase definida en código .iri.

    Uso .iri:
        class Usuario():
            var nombre = ""
            var email  = ""

            def saludar():
                out "Hola, soy {nombre}"
            end

            def set_nombre(n):
                nombre = n
            end
        end

        var u = Usuario()
        u.set_nombre("Ana")
        u.saludar()
    """

    def __init__(self, name, fields, methods, engine):
        self._name    = name
        self._fields  = fields
        self._methods = methods
        self._engine  = engine

    def __call__(self, *args):
        inst = IridiumInstance(self._name, dict(self._fields), self._methods, self._engine)
        if "__init__" in self._methods:
            inst._call_method("__init__", list(args))
        return inst

    def __repr__(self):
        return f"<clase {self._name}>"


class IridiumInstance(IridiumObject):
    def __init__(self, class_name, fields, methods, engine):
        super().__init__(fields)
        object.__setattr__(self, "_cn",  class_name)
        object.__setattr__(self, "_mth", methods)
        object.__setattr__(self, "_eng", engine)

    def _call_method(self, name, args=None):
        eng  = object.__getattribute__(self, "_eng")
        mths = object.__getattribute__(self, "_mth")
        if name not in mths:
            raise AttributeError(f"Método '{name}' no existe")
        prev      = dict(eng.variables)
        prev_ret  = eng._return_value
        eng._return_value = None
        # Inyectar campos de la instancia como variables locales
        eng.variables.update(dict(self))
        lines = mths[name]
        param_names = []
        if lines and isinstance(lines[0], list):
            param_names = lines[0]
            lines       = lines[1:]
        for pn, pv in zip(param_names, args or []):
            eng.variables[pn] = pv
        # Usar _exec_block para soporte completo de if/else/while/for
        eng._exec_block(lines, 0, len(lines))
        # Sincronizar campos modificados de vuelta a la instancia
        for k in list(dict(self).keys()):
            if k in eng.variables:
                self[k] = eng.variables[k]
        retval = eng._return_value
        eng.variables     = prev
        eng._return_value = prev_ret
        return retval

    def __getattr__(self, name):
        mths = object.__getattribute__(self, "_mth")
        if name in mths:
            def _bound(*args):
                return self._call_method(name, list(args))
            return _bound
        return dict.get(self, name)

    def __repr__(self):
        cn = object.__getattribute__(self, "_cn")
        return f"<{cn} {dict.__repr__(self)}>"


# ==============================================================================
#  HTTP HANDLER
# ==============================================================================

def _make_handler(router: IridiumRouter):
    class _H(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # silenciar log por defecto

        def _send(self, resp: IridiumResponse):
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.content_type)
            self.send_header("Access-Control-Allow-Origin",  "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            encoded = resp.body.encode("utf-8") if isinstance(resp.body, str) else resp.body
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            print(f"   🌐 {self.command} {self.path}  →  {resp.status}")

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin",  "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()

        def _handle(self):
            parsed = urlparse(self.path)
            path   = parsed.path
            params = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}
            body   = {}
            length = int(self.headers.get("Content-Length", 0))
            if length:
                raw = self.rfile.read(length).decode("utf-8")
                try:    body = json.loads(raw)
                except: body = {}
            resp = router.dispatch(path, self.command, body, params, {})
            if resp is None:
                resp = IridiumResponse("{}", 200)
            if not isinstance(resp, IridiumResponse):
                resp = jsonify(resp)
            self._send(resp)

        do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _handle

    return _H


# ==============================================================================
#  MOTOR IRIDIUM V2
# ==============================================================================

class IridiumEngine:

    def __init__(self):
        self.variables             = {}
        self.constantes            = set()
        self.env_data              = {}
        self.modo_secure           = False
        self.in_multiline_comment  = False
        self.block_stack           = []
        self._return_value         = None

        self.router   = IridiumRouter()
        self.db       = IridiumDB()
        self._clases  = {}

        self.lib_nativa = {
            # Matemáticas
            "math"           : IridiumMath(),
            "ia"             : IridiumIA(),
            "sqrt"           : math.sqrt,
            "pow"            : math.pow,
            "avrg"           : lambda x: sum(x) / len(x) if x else 0,
            "tensor"         : lambda x: x,
            # Tipos Python útiles
            "list"           : list,
            "range"          : range,
            "len"            : len,
            "str"            : str,
            "int"            : int,
            "float"          : float,
            "bool"           : bool,
            "abs"            : abs,
            "round"          : round,
            "IridiumObject"  : IridiumObject,
            # Web nativo
            "jsonify"        : jsonify,
            "html"           : html,
            # Base de datos nativa
            "db"             : self.db,
            # Seguridad
            "hash_password"  : generate_password_hash,
            "check_password" : check_password_hash,
            # Constantes
            "True"  : True,
            "False" : False,
            "None"  : None,
        }

    # ─── helpers ──────────────────────────────────────────────────────────────

    def _ctx(self):
        return {**self.lib_nativa, **self.variables, **self._clases}

    def eval_expr(self, expr: str, strict=False):
        try:
            expr = expr.strip()
            expr = expr.replace("true", "True").replace("false", "False").replace("null", "None")
            expr = re.sub(r'\[(\d+)\.\.(\d+)\]', r'list(range(\1, \2+1))', expr)
            return eval(expr, {"__builtins__": {
                "len": len, "str": str, "int": int, "float": float,
                "bool": bool, "list": list, "dict": dict, "range": range,
                "abs": abs, "round": round, "True": True, "False": False, "None": None,
                "isinstance": isinstance,
            }}, self._ctx())
        except Exception as e:
            if strict: raise e
            return expr.strip('"').strip("'")

    def cargar_env(self, ruta: str):
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                for linea in f:
                    linea = linea.strip()
                    if linea and "=" in linea and not linea.startswith("#"):
                        k, v = linea.split("=", 1)
                        self.env_data[k.strip()]  = v.strip()
                        self.variables[k.strip()] = v.strip()
            print(f"⚙️  [Env] Cargado: {ruta}")

    # ─── out ──────────────────────────────────────────────────────────────────

    def _procesar_out(self, linea: str):
        m = re.search(r'"([^"]*)"', linea)
        if not m: return
        texto = m.group(1)
        for tag in re.findall(r'\{([^}]*)\}', texto):
            expr = tag.split(",")[0].strip()
            try:
                val = str(self.eval_expr(expr))
            except Exception:
                val = "Indefinido"
            if self.modo_secure and "encrypted: false" not in tag:
                val = "********"
            texto = texto.replace(f"{{{tag}}}", val)
        print(texto)

    # ─── asignación ───────────────────────────────────────────────────────────

    def _procesar_asignacion(self, linea: str):
        es_const = "const " in linea
        limpia   = linea.replace("const ", "").replace("var ", "")

        if "~>" in limpia:
            izq, der = limpia.split("~>", 1)
            nombre   = izq.split("=", 1)[0].split(":")[0].strip()
            try:    valor = self.eval_expr(izq.split("=", 1)[1].strip(), strict=True)
            except: valor = self.eval_expr(der.strip())
        elif "=" in limpia:
            nombre  = limpia.split("=", 1)[0].split(":")[0].strip()
            val_raw = limpia.split("=", 1)[1].strip()
            if nombre in self.constantes:
                print(f"[Ir-Error Fatal] Constante '{nombre}' protegida en memoria.")
                sys.exit(1)
            # obj.campo = valor
            if "." in nombre:
                parts = nombre.split(".", 1)
                obj   = self.variables.get(parts[0])
                if isinstance(obj, dict):
                    obj[parts[1]] = self.eval_expr(val_raw)
                return
            valor = self.eval_expr(val_raw)
        else:
            return

        self.variables[nombre] = valor
        if es_const: self.constantes.add(nombre)

    # ─── busca el índice de la próxima línea no-vacía/no-comentario ──────────────

    def _next_real(self, lineas, start):
        """Retorna el índice de la próxima línea real (no vacía, no comentario)."""
        j = start
        while j < len(lineas):
            l = lineas[j].strip() if isinstance(lineas[j], str) else str(lineas[j]).strip()
            if l and not l.startswith("//"):
                return j
            j += 1
        return j

    # ─── salta físicamente un bloque if/else completo ─────────────────────────

    def _skip_if_block(self, lineas, start):
        """
        Dado que estamos en la línea DESPUÉS de un 'if ...:' que es False,
        saltamos hasta encontrar el 'else:' del mismo nivel, o hasta que
        terminemos el bloque (detectado porque la siguiente línea es un
        statement de nivel superior, no indentado).
        Retorna el índice donde debe continuar la ejecución.
        """
        i = start
        while i < len(lineas):
            l = lineas[i].strip() if isinstance(lineas[i], str) else str(lineas[i]).strip()
            if not l or l.startswith("//"):
                i += 1; continue
            # ¿Es el else de este if?
            if l == "else:":
                return i  # el llamador procesará el else:
            # ¿Es otro bloque de nivel superior? (no indentado → fin del if)
            raw = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
            if raw and raw[0] != ' ' and raw[0] != '\t' and l:
                return i  # llegamos a código de nivel raíz sin else
            i += 1
        return i

    def _skip_else_block(self, lineas, start):
        """
        Saltamos el bloque else (porque el if fue True).
        Retorna el índice donde continúa la ejecución después del else.
        """
        i = start
        while i < len(lineas):
            l = lineas[i].strip() if isinstance(lineas[i], str) else str(lineas[i]).strip()
            if not l or l.startswith("//"):
                i += 1; continue
            raw = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
            if raw and raw[0] != ' ' and raw[0] != '\t' and l:
                return i
            i += 1
        return i

    # ─── _ejecutar_lineas (para métodos y routes) ─────────────────────────────

    def _ejecutar_lineas(self, lineas: list):
        i = 0
        while i < len(lineas):
            linea = lineas[i].strip() if isinstance(lineas[i], str) else str(lineas[i]).strip()
            if not linea or linea.startswith("//"): i += 1; continue

            if linea.startswith("return "):
                self._return_value = self.eval_expr(linea[7:].strip())
                return

            if linea.startswith("out "):
                self._procesar_out(linea); i += 1; continue

            if linea.startswith("if ") and linea.endswith(":"):
                cond = linea[3:-1].strip()
                res  = bool(self.eval_expr(cond))
                if res:
                    # ejecutar el bloque if (líneas indentadas que siguen)
                    i += 1
                    while i < len(lineas):
                        l2 = lineas[i].strip() if isinstance(lineas[i], str) else str(lineas[i]).strip()
                        raw2 = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
                        if not l2 or l2.startswith("//"):
                            i += 1; continue
                        if l2 == "else:":
                            # saltar el bloque else
                            i += 1
                            while i < len(lineas):
                                l3 = lineas[i].strip() if isinstance(lineas[i], str) else str(lineas[i]).strip()
                                raw3 = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
                                if not l3 or l3.startswith("//"): i += 1; continue
                                if raw3 and raw3[0] not in (' ','\t'): break
                                i += 1
                            break
                        if raw2 and raw2[0] not in (' ', '\t'):
                            break  # fin del bloque if
                        # ejecutar línea del bloque
                        self._ejecutar_lineas([l2])
                        if self._return_value is not None: return
                        i += 1
                else:
                    # saltar el bloque if, buscar else
                    i += 1
                    found_else = False
                    while i < len(lineas):
                        l2 = lineas[i].strip() if isinstance(lineas[i], str) else str(lineas[i]).strip()
                        raw2 = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
                        if not l2 or l2.startswith("//"): i += 1; continue
                        if l2 == "else:":
                            found_else = True
                            i += 1; break
                        if raw2 and raw2[0] not in (' ', '\t'): break
                        i += 1
                    if found_else:
                        # ejecutar bloque else
                        while i < len(lineas):
                            l2 = lineas[i].strip() if isinstance(lineas[i], str) else str(lineas[i]).strip()
                            raw2 = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
                            if not l2 or l2.startswith("//"): i += 1; continue
                            if raw2 and raw2[0] not in (' ', '\t'): break
                            self._ejecutar_lineas([l2])
                            if self._return_value is not None: return
                            i += 1
                continue

            if ("=" in linea or "var " in linea or "const " in linea) and not linea.startswith("out "):
                self._procesar_asignacion(linea); i += 1; continue

            try: self.eval_expr(linea)
            except Exception: pass
            i += 1

    # ─── parseo de clase ──────────────────────────────────────────────────────

    def _parsear_clase(self, lineas, idx):
        header = lineas[idx].strip()
        m = re.match(r'class\s+(\w+)\s*(?:\(.*\))?\s*:', header)
        if not m: return None, idx + 1
        name    = m.group(1)
        fields  = {}
        methods = {}
        i       = idx + 1
        depth   = 1

        while i < len(lineas):
            l = lineas[i].strip() if isinstance(lineas[i], str) else str(lineas[i]).strip()

            if not l or l.startswith("//"): i += 1; continue

            # ── Fin de bloque ──────────────────────────────────────────────
            if l == "end":
                depth -= 1
                if depth == 0: break   # fin de esta clase
                i += 1; continue

            # ── Contenido de nivel 1 (directo dentro de la clase) ──────────
            if depth == 1:
                # Campo: var nombre = valor
                if (l.startswith("var ") or l.startswith("const ")) and "=" in l:
                    clean = l.replace("var ", "").replace("const ", "")
                    fn = clean.split("=")[0].strip()
                    fv = self.eval_expr(clean.split("=", 1)[1].strip())
                    fields[fn] = fv
                    i += 1; continue

                # Método: function nombre(params):
                elif l.startswith("function ") and l.endswith(":"):
                    m2 = re.match(r'function\s+(\w+)\s*\(([^)]*)\)\s*:', l)
                    if m2:
                        mname  = m2.group(1)
                        params = [p.strip() for p in m2.group(2).split(",") if p.strip()]
                        mlines = [params]
                        j  = i + 1
                        md = 1
                        while j < len(lineas):
                            # Preservar la línea RAW (con indentación) para que if/else funcione
                            raw_ml = lineas[j] if isinstance(lineas[j], str) else str(lineas[j])
                            ml = raw_ml.strip()
                            if not ml or ml.startswith("//"): j += 1; continue
                            # Solo bloques reales suben depth
                            if (ml.startswith("function ") or ml.startswith("while ") or
                                ml.startswith("for ") or ml.startswith("class ") or
                                ml.startswith("secure:")) and ml.endswith(":"):
                                md += 1
                            if ml == "end":
                                md -= 1
                                if md == 0: break
                            mlines.append(raw_ml)   # ← guardar con indentación
                            j += 1
                        methods[mname] = mlines
                        i = j + 1  # saltar el 'end' del método
                        continue

            # ── Bloques anidados (while/for/class dentro de método ya capturado) ──
            if (l.startswith("function ") or l.startswith("while ") or
                l.startswith("for ") or l.startswith("class ") or
                l.startswith("secure:")) and l.endswith(":"):
                depth += 1

            i += 1

        cls = IridiumClass(name, fields, methods, self)
        self._clases[name]    = cls
        self.lib_nativa[name] = cls
        self.variables[name]  = cls
        print(f"📦 [Clase] '{name}' → campos: {list(fields.keys())}  métodos: {list(methods.keys())}")
        return cls, i + 1

    # ─── parseo de route ──────────────────────────────────────────────────────

    def _parsear_route(self, lineas, idx):
        header = lineas[idx].strip()

        pm = re.search(r'["\']([^"\']+)["\']', header)
        if not pm: return idx + 1
        path = pm.group(1)

        # métodos HTTP después del =>
        methods = re.findall(r'"(GET|POST|PUT|DELETE|PATCH)"', header.upper())
        if not methods:
            methods = re.findall(r"'(GET|POST|PUT|DELETE|PATCH)'", header.upper())
        if not methods:
            methods = ["GET"]

        # Recolectar cuerpo hasta 'end' — depth solo sube con bloques reales
        body_lines = []
        i     = idx + 1
        depth = 1
        while i < len(lineas):
            raw = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
            l   = raw.strip()          # strip() elimina \r\n y espacios
            # Solo bloques con su propio 'end' suben el depth
            if (l.startswith("while ") or l.startswith("for ") or
                l.startswith("secure:") or l.startswith("class ") or
                l.startswith("function ")) and l.endswith(":"):
                depth += 1
            if l == "end":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            body_lines.append(raw)
            i += 1

        snap_vars  = dict(self.variables)
        eng_ref    = self

        def handler(body: dict, params: dict, path_params: dict):
            sub = IridiumEngine()
            sub.db             = eng_ref.db
            sub._clases        = dict(eng_ref._clases)
            sub.lib_nativa     = {**eng_ref.lib_nativa}
            sub.lib_nativa["db"] = eng_ref.db
            sub.env_data       = eng_ref.env_data
            sub.variables      = {
                **snap_vars,
                **eng_ref.variables,
                **eng_ref._clases,
                "body"       : IridiumObject(body),
                "params"     : IridiumObject(params),
                "path_params": IridiumObject(path_params),
                **body,
                **path_params,
            }
            sub._return_value = None
            sub._exec_block(body_lines, 0, len(body_lines))
            rv = sub._return_value
            if rv is None:                                               rv = jsonify({"ok": True})
            if isinstance(rv, dict) and not isinstance(rv, IridiumResponse): rv = jsonify(rv)
            if isinstance(rv, str)  and not isinstance(rv, IridiumResponse): rv = jsonify({"mensaje": rv})
            return rv

        self.router.add(path, methods, handler)
        return i + 1

    # ─── ejecución principal ──────────────────────────────────────────────────

    def ejecutar_archivo(self, ruta: str):
        if not ruta:
            print("Uso: python main.py <archivo.iri>")
            return
        try:
            with open(ruta, encoding="utf-8") as f:
                contenido = f.read()
            # Normalizar saltos de línea Windows (\r\n) y Mac clásico (\r)
            contenido = contenido.replace('\r\n', '\n').replace('\r', '\n')
            lineas = [l + '\n' for l in contenido.split('\n')]
        except FileNotFoundError:
            print(f"[Ir-Error] Archivo no encontrado: {ruta}")
            return
        self._exec_block(lineas, 0, len(lineas))

    def _recolectar_bloque_end(self, lineas, start, end_idx):
        """Recolecta líneas hasta encontrar 'end'. Retorna (lines, next_i)."""
        body  = []
        i     = start
        depth = 1
        while i < end_idx:
            raw = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
            l   = raw.strip()
            if (l.startswith("while ") or l.startswith("for ") or
                l.startswith("secure:") or l.startswith("class ") or
                l.startswith("function ")) and l.endswith(":"):
                depth += 1
            if l == "end":
                depth -= 1
                if depth == 0:
                    return body, i + 1
            body.append(raw)
            i += 1
        return body, i

    def _exec_block(self, lineas, start, end_idx):
        """Ejecuta lineas[start:end_idx] como bloque principal."""
        i = start
        while i < end_idx:
            raw   = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
            linea = raw.strip()

            # ── Comentarios multilínea ─────────────────────────────────────
            if "/*" in linea: self.in_multiline_comment = True
            if self.in_multiline_comment:
                if "*/" in linea: self.in_multiline_comment = False
                i += 1; continue
            if not linea or linea.startswith("//"): i += 1; continue

            # ── CLASE ─────────────────────────────────────────────────────
            if linea.startswith("class ") and linea.endswith(":"):
                _, i = self._parsear_clase(lineas, i)
                continue

            # ── ROUTE ─────────────────────────────────────────────────────
            if linea.startswith("route "):
                i = self._parsear_route(lineas, i)
                continue

            # ── SERVE ─────────────────────────────────────────────────────
            if linea.startswith("serve("):
                m = re.search(r'serve\((\d+)(?:,\s*"([^"]*)")?\)', linea)
                port = int(m.group(1)) if m else 5000
                host = m.group(2) if m and m.group(2) else "0.0.0.0"
                HTTPServer.allow_reuse_address = True
                handler = _make_handler(self.router)
                srv = HTTPServer((host, port), handler)
                t = threading.Thread(target=srv.serve_forever, daemon=True)
                t.start()
                print(f"\n🚀 [Iridium Web] Escuchando en http://{host}:{port}", flush=True)
                print("   Ctrl+C para detener.\n", flush=True)
                try:
                    while t.is_alive():
                        _time_module.sleep(0.5)
                except KeyboardInterrupt:
                    print("\n🛑 Servidor detenido.", flush=True)
                    srv.shutdown()
                    srv.server_close()
                return
            # ── ENV ───────────────────────────────────────────────────────
            if linea.startswith("env of"):
                m = re.search(r'"([^"]*)"', linea)
                if m: self.cargar_env(m.group(1))
                i += 1; continue

            # ── >> out ────────────────────────────────────────────────────
            if linea.endswith(">> out"):
                vn = linea.replace(">> out", "").strip()
                print(f">> {self.variables.get(vn, '[Indefinido]')}")
                i += 1; continue

            # ── SECURE (tiene end) ─────────────────────────────────────────
            if linea.startswith("secure:"):
                self.modo_secure = True
                i += 1
                while i < end_idx:
                    r2 = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
                    l2 = r2.strip()
                    if l2 == "end": self.modo_secure = False; i += 1; break
                    if l2 and not l2.startswith("//"): self._exec_single(l2)
                    i += 1
                continue

            # ── IF / ELSE  (sin end, delimitado por indentación) ───────────
            if linea.startswith("if ") and linea.endswith(":"):
                cond = linea[3:-1].strip()
                res  = bool(self.eval_expr(cond))
                i   += 1
                if_lines, else_lines = [], []
                in_else = False
                while i < end_idx:
                    r2  = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
                    l2  = r2.strip()
                    if not l2 or l2.startswith("//"):
                        i += 1; continue
                    is_indented = len(r2) > 0 and r2[0] in (' ', '\t')
                    if not is_indented:
                        if l2 == "else:":
                            in_else = True; i += 1; continue
                        else:
                            break  # fin del if
                    (else_lines if in_else else if_lines).append(l2)
                    i += 1
                for ln in (if_lines if res else else_lines):
                    self._exec_single(ln)
                continue

            # ── WHILE (tiene end) ──────────────────────────────────────────
            if linea.startswith("while ") and linea.endswith(":"):
                cond  = linea[6:-1].strip().strip("()")
                body, i = self._recolectar_bloque_end(lineas, i + 1, end_idx)
                while bool(self.eval_expr(cond)):
                    for ln in body:
                        self._exec_single(ln.strip() if isinstance(ln, str) else str(ln).strip())
                continue

            # ── FOR (tiene end) ────────────────────────────────────────────
            if linea.startswith("for ") and linea.endswith(":"):
                partes     = linea[4:-1].strip().strip("()").split(";")
                init_part  = partes[0].replace("var","").strip()
                cond       = partes[1].strip()
                step       = partes[2].strip()
                vn, vv     = init_part.split("=")
                vn         = vn.strip()
                self.variables[vn] = int(vv.strip())
                body, i = self._recolectar_bloque_end(lineas, i + 1, end_idx)
                while bool(self.eval_expr(cond)):
                    for ln in body:
                        self._exec_single(ln.strip() if isinstance(ln, str) else str(ln).strip())
                    if "++" in step:
                        sv = step.replace("++","").strip()
                        self.variables[sv] = self.variables.get(sv, 0) + 1
                    elif "--" in step:
                        sv = step.replace("--","").strip()
                        self.variables[sv] = self.variables.get(sv, 0) - 1
                continue

            # ── SWITCH (sin end, case/default son inline) ──────────────────
            if linea.startswith("switch"):
                vn  = linea.split("(")[1].split(")")[0].strip()
                val = self.variables.get(vn)
                i  += 1
                matched = False
                while i < end_idx:
                    r2 = lineas[i] if isinstance(lineas[i], str) else str(lineas[i])
                    l2 = r2.strip()
                    if not l2 or l2.startswith("//"): i += 1; continue
                    if not l2.startswith("case ") and not l2.startswith("default:"):
                        break
                    if l2.startswith("case "):
                        parts    = l2.split(":", 1)
                        case_val = parts[0].replace("case","").strip().strip('"').strip("'")
                        if not matched and str(val) == case_val:
                            matched = True
                            if len(parts) > 1 and parts[1].strip():
                                self._exec_single(parts[1].strip())
                    elif l2.startswith("default:"):
                        if not matched:
                            action = l2.split(":", 1)[1].strip()
                            if action: self._exec_single(action)
                        i += 1; break
                    i += 1
                continue

            # ── Todo lo demás ──────────────────────────────────────────────
            self._exec_single(linea)
            i += 1

    def _exec_single(self, linea: str):
        """Ejecuta una sola línea de código Iridium."""
        linea = linea.strip()
        if not linea or linea.startswith("//"): return

        if linea.startswith("return "):
            self._return_value = self.eval_expr(linea[7:].strip()); return

        if linea.startswith("out "):
            self._procesar_out(linea); return

        if linea.endswith(">> out"):
            vn = linea.replace(">> out","").strip()
            print(f">> {self.variables.get(vn,'[Indefinido]')}"); return

        if " += " in linea:
            p = linea.split(" += ", 1)
            cv = self.eval_expr(p[1])
            try: cv = float(cv)
            except: pass
            self.variables[p[0].strip()] = self.variables.get(p[0].strip(), 0) + cv; return

        if " -= " in linea:
            p = linea.split(" -= ", 1)
            cv = self.eval_expr(p[1])
            try: cv = float(cv)
            except: pass
            self.variables[p[0].strip()] = self.variables.get(p[0].strip(), 0) - cv; return

        if ("=" in linea or "var " in linea or "const " in linea) and not linea.startswith("out "):
            if "FROM env.file" in linea:
                partes = linea.split("=")[0] if "=" in linea else linea.split("FROM")[0]
                nombre = partes.replace("const","").replace("var","").strip().split(":")[0].strip()
                val    = self.env_data.get(nombre, "")
                self.variables[nombre] = int(val) if str(val).isdigit() else val
                return
            self._procesar_asignacion(linea); return

        try: self.eval_expr(linea)
        except Exception: pass


# ==============================================================================
#  PUNTO DE ENTRADA
# ==============================================================================

BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║             Iridium V2.0  —  Native Web Edition               ║
╠═══════════════════════════════════════════════════════════════╣
║  Uso:  python main.py <archivo.iri>                           ║
╠═══════════════════════════════════════════════════════════════╣
║  RUTAS WEB                                                    ║
║   route "/ruta" => "GET":                                     ║
║       return jsonify({"ok": true})                            ║
║   end                                                         ║
║   route "/ruta/<id>" => "POST", "DELETE":                     ║
║       var usuario_id = id                                     ║
║       return jsonify({"id": usuario_id})                      ║
║   end                                                         ║
║   serve(5000)                                                 ║
╠═══════════════════════════════════════════════════════════════╣
║  BASE DE DATOS                                                ║
║   db.config("localhost", "root", "", "mi_base")               ║
║   var filas = db.query("SELECT * FROM tabla")                 ║
║   var fila  = db.query_one("SELECT * FROM t WHERE id=?", id)  ║
║   var r     = db.exec("INSERT INTO t (col) VALUES (?)", val)  ║
║   out "ID nuevo: {r.last_id}"                                 ║
╠═══════════════════════════════════════════════════════════════╣
║  CLASES                                                       ║
║   class Persona():                                            ║
║       var nombre = ""                                         ║
║       function saludar():                                     ║
║           out "Hola, soy {nombre}"                            ║
║       end                                                     ║
║   end                                                         ║
║   var p = Persona()                                           ║
║   p.nombre = "Ana"                                            ║
║   p.saludar()                                                 ║
╠═══════════════════════════════════════════════════════════════╣
║  SEGURIDAD                                                    ║
║   var h  = hash_password("texto")                             ║
║   var ok = check_password(h, "texto")                         ║
╚═══════════════════════════════════════════════════════════════╝
"""

if __name__ == "__main__":
    engine = IridiumEngine()
    if len(sys.argv) > 1:
        engine.ejecutar_archivo(sys.argv[1])
    else:
        print(BANNER)