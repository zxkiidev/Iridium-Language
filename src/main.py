import re
import sys
import io

# Forzar salida en UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class IridiumEngine:
    def __init__(self):
        self.variables = {}
        self.constantes = [] 
        self.saltar_bloque = False 
        self.if_cumplido = False # <--- NUEVO: Para saber si saltar el ELSE
        self.modo_env = False 
        self.modo_secure = False 

    def ejecutar_archivo(self, ruta_archivo):
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                 lineas = f.readlines()
                 i = 0
                 while i < len(lineas):
                     i = self.procesar_linea(lineas[i], i)
                     i += 1
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo {ruta_archivo}")

    def validar_tipo(self, nombre, tipo, valor):
        tipos_map = {"int": int, "float": (float, int), "string": str, "bool": bool}
        if tipo in tipos_map:
            if not isinstance(valor, tipos_map[tipo]):
                raise TypeError(f"[Ir-Error]: La variable '{nombre}' espera un '{tipo}' pero recibió '{type(valor).__name__}'")

    def procesar_linea(self, linea_original, indice_actual=0):
        linea_stripped = linea_original.strip()
        
        # Manejo de fin de bloque
        if linea_stripped == "end":
            self.saltar_bloque = False
            self.modo_secure = False
            return indice_actual

        # Reiniciar saltar_bloque solo si no estamos en una indentación
        if linea_original.strip() and not (linea_original.startswith("    ") or linea_original.startswith("\t")):
            # Si la línea es un 'else:', no reiniciamos saltar_bloque todavía
            if not linea_stripped.startswith("else:"):
                if not self.modo_secure:
                    self.saltar_bloque = False
                self.modo_env = False

        # Si estamos saltando bloque, solo escuchamos al 'else:' o al 'end'
        if self.saltar_bloque and not linea_stripped.startswith("else:"):
            return indice_actual

        if not linea_stripped or linea_stripped.startswith("//"):
            return indice_actual

        # --- LÓGICA: IF ---
        if linea_stripped.startswith("if ") and linea_stripped.endswith(":"):
            cond = linea_stripped[3:-1].strip().replace("(", "").replace(")", "")
            # Reemplazar variables (de la más larga a la más corta para evitar errores)
            for v_n in sorted(self.variables.keys(), key=len, reverse=True):
                if v_n in cond:
                    cond = cond.replace(v_n, str(self.variables[v_n]))
            
            cond = cond.replace("true", "True").replace("false", "False")
            
            self.if_cumplido = eval(cond)
            self.saltar_bloque = not self.if_cumplido
            return indice_actual

        # --- LÓGICA: ELSE ---
        if linea_stripped.startswith("else:"):
            # Si el IF se cumplió, el ELSE debe saltarse.
            # Si el IF NO se cumplió, el ELSE NO debe saltarse.
            self.saltar_bloque = self.if_cumplido
            return indice_actual

        # --- LÓGICA: SECURE ---
        if linea_stripped.startswith("secure:"):
            self.modo_secure = True
            return indice_actual

        # --- LÓGICA: MIRROR LOG (>> out) ---
        if " >> out" in linea_stripped:
            target = linea_stripped.split(">> out")[0].strip().split(":")[0].strip()
            if target in self.variables:
                val = "********" if self.modo_secure else self.variables[target]
                print(f"[MIRROR LOG]: {target} = {val}")
            return indice_actual

        # --- LÓGICA: ASIGNACIÓN COMPUESTA ---
        if any(op in linea_stripped for op in ["+=", "*=", "++"]) and not linea_stripped.startswith("var "):
            if "++" in linea_stripped:
                var_n = linea_stripped.replace("++", "").strip()
                if var_n in self.variables: self.variables[var_n] += 1
            else:
                for op in ["+=", "*="]:
                    if op in linea_stripped:
                        var_n, val_ext = linea_stripped.split(op)
                        var_n = var_n.strip()
                        if var_n in self.variables:
                            self.variables[var_n] = eval(f"{self.variables[var_n]} {op[0]} {val_ext}")
            return indice_actual

        # --- LÓGICA: CONSTANTES ---
        if linea_stripped.startswith("const "):
            partes = linea_stripped.replace("const ", "").split("=", 1)
            nombre = partes[0].split(":")[0].strip()
            self.constantes.append(nombre)
            valor_raw = partes[1].split("FROM")[0].strip() if "=" in linea_stripped else "0"
            valor_raw = valor_raw.replace("true", "True").replace("false", "False")
            self.variables[nombre] = eval(valor_raw)
            return indice_actual

        # --- LÓGICA: VARIABLES Y SPONGE ---
        if linea_stripped.startswith("var "):
            partes_igual = linea_stripped[4:].split("=", 1)
            meta = partes_igual[0].strip()
            nombre_real = meta.split(":")[0].strip()
            
            if nombre_real in self.constantes:
                print(f"[Ir-Error]: No se puede reasignar la constante '{nombre_real}'")
                sys.exit(1)

            # --- NUEVA LÓGICA: INPUT (await) ---
            if "await" in partes_igual[1]:
                # Extraemos el mensaje dentro de las comillas después de await
                mensaje_match = re.search(r'await\s+"([^"]*)"', partes_igual[1])
                prompt = mensaje_match.group(1) if mensaje_match else ""
                
                # Pausamos el motor para recibir el dato del usuario
                valor_usuario = input(prompt)
                
                # Intentamos convertir a número si es posible, si no, se queda como string
                try:
                    if "." in valor_usuario: valor_final = float(valor_usuario)
                    else: valor_final = int(valor_usuario)
                except ValueError:
                    valor_final = valor_usuario
            
            # --- LÓGICA ORIGINAL (Sponge y eval) ---
            else:
                valor_raw = linea_stripped.split("~>")[1].strip() if "~>" in linea_stripped else partes_igual[1].strip()
                valor_raw = valor_raw.replace("true", "True").replace("false", "False")
                
                for v_n in sorted(self.variables.keys(), key=len, reverse=True):
                    if v_n in valor_raw:
                        valor_raw = valor_raw.replace(v_n, str(self.variables[v_n]))
                
                try:
                    valor_final = eval(valor_raw)
                except:
                    valor_final = valor_raw.strip('"')

            # Validación de tipo (funciona igual para el input)
            if ":" in meta:
                self.validar_tipo(nombre_real, meta.split(":")[1].strip(), valor_final)

            self.variables[nombre_real] = valor_final
            return indice_actual

        # --- LÓGICA: OUT ---
        elif linea_stripped.startswith("out "):
            matches = re.findall(r'"([^"]*)"', linea_stripped)
            if matches:
                texto = matches[0]
                variables_en_texto = re.findall(r'\{([^}]*)\}', texto)
                for item in variables_en_texto:
                    nombre_var = item.split(",")[0].strip()
                    if nombre_var in self.variables:
                        if "encrypted: false" in item:
                            val = str(self.variables[nombre_var])
                        else:
                            val = "********" if self.modo_secure else str(self.variables[nombre_var])
                        texto = texto.replace(f"{{{item}}}", val)
                print(texto)
        
        return indice_actual

if __name__ == "__main__":
    engine = IridiumEngine()
    archivo = sys.argv[1] if len(sys.argv) > 1 else input("Archivo .iri: ")
    print("\n>>> [IRIDIUM ENGINE ACTIVE]")
    engine.ejecutar_archivo(archivo)
    print(">>> [EJECUCIÓN FINALIZADA]\n")