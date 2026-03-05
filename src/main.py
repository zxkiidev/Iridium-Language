import re
import sys
import io
import math
import os

# Forzar salida en UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- CLASES Y OBJETOS NATIVOS DE IRIDIUM ---
class IridiumObject(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

class IridiumMath:
    sqrt = math.sqrt
    pow = math.pow

class IridiumIA:
    def predict(self, data, mod):
        return f"Tensor({data}) procesado por {mod}"

class DummyDB:
    def __init__(self, motor, host):
        self.motor = motor
        self.host = host
    
    def fetchAll(self):
        # Simulamos una caída real del servidor para que Sponge (~>) actúe
        raise Exception("Timeout: Base de datos no responde")

class IridiumEngine:
    def __init__(self):
        self.variables = {}
        self.constantes = set()
        self.env_data = {}
        self.modo_secure = False
        self.in_multiline_comment = False
        self.block_stack = [] 

        # --- LIBRERÍA NATIVA V1.2 (Sólida) ---
        self.lib_nativa = {
            "math": IridiumMath(),
            "ia": IridiumIA(),
            # Funciones matemáticas directas para evitar errores de punto
            "sqrt": math.sqrt,
            "pow": math.pow,
            "avrg": lambda x: sum(x) / len(x) if x else 0,
            "tensor": lambda x: x,
            "list": list,
            "range": range,
            "IridiumObject": IridiumObject
        }

    def eval_expr(self, expr, strict=False):
        """Evalúa expresiones. Si strict=True, lanza errores (vital para Sponge ~>)"""
        try:
            expr = expr.replace("true", "True").replace("false", "False")
            
            # Rangos [1..100] -> list(range(1, 101))
            expr = re.sub(r'\[(\d+)\.\.(\d+)\]', r'list(range(\1, \2 + 1))', expr)
            
            # Datasets {1, 2} -> [1, 2]
            if "{" in expr and "}" in expr and not expr.startswith("IridiumObject"):
                expr = expr.replace("{", "[").replace("}", "]")

            # Mock para la conexión a DB que tiene sintaxis especial (host: DB_HOST)
            if "connect(" in expr:
                return DummyDB(self, "localhost")

            ctx = {**self.lib_nativa, **self.variables}
            return eval(expr, {"__builtins__": None}, ctx)
        except Exception as e:
            if strict: raise e # Si es estricto, lanzamos el error
            return expr.strip('"').strip("'")

    def cargar_env(self, ruta):
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                for linea in f:
                    if '=' in linea and not linea.strip().startswith("#"):
                        k, v = linea.split('=', 1)
                        self.env_data[k.strip()] = v.strip()

    def ejecutar_archivo(self, ruta_archivo):
        if not ruta_archivo:
            print("Uso: python main.py <archivo.iri>")
            return

        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                lineas = f.readlines()
        except FileNotFoundError:
            return

        i = 0
        while i < len(lineas):
            linea = lineas[i].strip()

            if "/*" in linea: self.in_multiline_comment = True
            if self.in_multiline_comment:
                if "*/" in linea: self.in_multiline_comment = False
                i += 1; continue

            if not linea or linea.startswith("//"):
                i += 1; continue

            if self.block_stack and self.block_stack[-1].get("skip", False):
                if linea == "end" or linea.startswith("else:"):
                    pass 
                else:
                    i += 1; continue

            if linea == "end":
                if self.block_stack:
                    bloque = self.block_stack.pop()
                    if bloque["type"] == "secure":
                        self.modo_secure = False
                    elif bloque["type"] == "while" and self.eval_expr(bloque["cond"]):
                        self.block_stack.append(bloque)
                        i = bloque["start_idx"]; continue
                    elif bloque["type"] == "for":
                        paso = bloque["step"]
                        if "++" in paso:
                            self.variables[paso.replace("++", "").strip()] += 1
                        if self.eval_expr(bloque["cond"]):
                            self.block_stack.append(bloque)
                            i = bloque["start_idx"]; continue
                i += 1; continue

            if linea.startswith("secure:"):
                self.modo_secure = True
                self.block_stack.append({"type": "secure", "skip": False})
                i += 1; continue

            if linea.startswith("env of"):
                self.cargar_env(re.search(r'"([^"]*)"', linea).group(1))
                i += 1; continue

            # --- SINTAXIS RAPIDA: dbpass >> out ---
            if linea.endswith(">> out"):
                var_name = linea.replace(">> out", "").strip()
                val = self.variables.get(var_name, "[Indefinido]")
                print(f">> {val}")
                i += 1; continue

            if linea.startswith("if ") and linea.endswith(":"):
                cond = linea[3:-1].strip()
                res = bool(self.eval_expr(cond))
                self.block_stack.append({"type": "if", "skip": not res, "handled": res})
                i += 1; continue

            if linea.startswith("else:"):
                if self.block_stack and self.block_stack[-1]["type"] == "if":
                    self.block_stack[-1]["skip"] = self.block_stack[-1]["handled"]
                i += 1; continue

            if linea.startswith("for ") and linea.endswith(":"):
                partes = linea[4:-1].strip().strip("()").split(";")
                init = partes[0].replace("var", "").strip()
                cond, step = partes[1].strip(), partes[2].strip()
                v_n, v_v = init.split("=")
                self.variables[v_n.strip()] = int(v_v.strip())
                res = bool(self.eval_expr(cond))
                self.block_stack.append({"type": "for", "start_idx": i + 1, "cond": cond, "step": step, "skip": not res})
                i += 1; continue

            if linea.startswith("while ") and linea.endswith(":"):
                cond = linea[6:-1].strip().strip("()")
                res = bool(self.eval_expr(cond))
                self.block_stack.append({"type": "while", "start_idx": i + 1, "cond": cond, "skip": not res})
                i += 1; continue

            if linea.startswith("switch"):
                var_name = linea.split("(")[1].split(")")[0].strip()
                self.block_stack.append({"type": "switch", "val": self.variables.get(var_name), "matched": False})
                i += 1; continue

            if linea.startswith("case ") and self.block_stack and self.block_stack[-1]["type"] == "switch":
                bloque_sw = self.block_stack[-1]
                if bloque_sw["matched"]: i += 1; continue
                partes_case = linea.split(":", 1)
                if str(bloque_sw["val"]) == partes_case[0].replace("case", "").strip().strip('"'):
                    bloque_sw["matched"] = True
                    if len(partes_case) > 1 and partes_case[1].strip():
                        lineas.insert(i + 1, partes_case[1].strip() + "\n")
                i += 1; continue
            
            if linea.startswith("default:") and self.block_stack and self.block_stack[-1]["type"] == "switch":
                if not self.block_stack[-1]["matched"]:
                    accion = linea.split(":", 1)[1].strip()
                    if accion: lineas.insert(i + 1, accion + "\n")
                i += 1; continue

            if " += " in linea or " -= " in linea:
                v_name, cant = re.split(r'\s*\+=\s*|\s*-=\s*', linea)
                cant_val = float(self.eval_expr(cant))
                if "+=" in linea: self.variables[v_name] += cant_val
                if "-=" in linea: self.variables[v_name] -= cant_val
                i += 1; continue

            # --- RED Y API (VERSIÓN CORREGIDA) ---
            if "=>" in linea and ("POST" in linea or "GET" in linea):
                endpoint_info = linea.split('=>')[0].strip()
                print(f"🌐 [Red] Endpoint registrado: {endpoint_info}")
                
                # Buscamos el final del bloque para no ejecutar el código interno ahora
                # (Ese código solo debe correr cuando alguien llame a la URL)
                j = i + 1
                while j < len(lineas) and lineas[j].strip() != "end":
                    j += 1
                
                i = j + 1 # Saltamos directamente después del 'end'
                continue

            if linea.startswith("serve("):
                print(f"🚀 [Iridium V1] Servidor Web levantado y escuchando peticiones.")
                i += 1; continue

            if ("=" in linea or "var " in linea or "const " in linea) and not linea.startswith("out "):
                if "FROM env.file" in linea:
                    partes = linea.split("=")[0] if "=" in linea else linea.split("FROM")[0]
                    nombre = partes.replace("const", "").replace("var", "").strip().split(":")[0].strip()
                    val = self.env_data.get(nombre, "")
                    self.variables[nombre] = int(val) if str(val).isdigit() else val
                    if "const " in linea: self.constantes.add(nombre)
                    i += 1; continue

                es_const = "const " in linea
                limpia = linea.replace("const ", "").replace("var ", "")
                
                if "~>" in limpia:
                    expr_izq, expr_der = limpia.split("~>", 1)
                    nombre = expr_izq.split("=", 1)[0].split(":")[0].strip()
                    try:
                        # Evaluamos estrictamente para forzar el error de red simulado
                        valor_final = self.eval_expr(expr_izq.split("=", 1)[1].strip(), strict=True)
                    except Exception as e:
                        # ¡Sponge te salva! Captura el error y usa el dataset de respaldo
                        valor_final = self.eval_expr(expr_der.strip())
                else:
                    nombre, val_raw = limpia.split("=", 1)[0].split(":")[0].strip(), limpia.split("=", 1)[1].strip()
                    if nombre in self.constantes:
                        print(f"[Ir-Error Fatal] Constante '{nombre}' protegida en memoria.")
                        sys.exit(1)
                    valor_final = self.eval_expr(val_raw)

                self.variables[nombre] = valor_final
                if es_const: self.constantes.add(nombre)
                i += 1; continue

            if linea.startswith("out "):
                texto_match = re.search(r'"([^"]*)"', linea)
                if texto_match:
                    texto = texto_match.group(1)
                    for v_match in re.findall(r'\{([^}]*)\}', texto):
                        v_base = v_match.split(",")[0].strip()
                        if "." in v_base:
                            val = str(self.variables.get(v_base.split(".")[0], {}).get(v_base.split(".")[1], "Indefinido"))
                        else:
                            val = str(self.variables.get(v_base, "Indefinido"))
                        if self.modo_secure and "encrypted: false" not in v_match: val = "********"
                        texto = texto.replace(f"{{{v_match}}}", val)
                    print(texto)
                i += 1; continue

            i += 1

if __name__ == "__main__":
    engine = IridiumEngine()
    if len(sys.argv) > 1:
        engine.ejecutar_archivo(sys.argv[1])
    else:
        print("Iridium V1.1 Core")