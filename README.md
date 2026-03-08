
# IRIDIUM

**A next-generation backend language built for resilience and AI.**

[![Version](https://img.shields.io/badge/version-v1.0-blue?style=flat-square)](https://github.com/zxkiidev/Iridium-Language/releases)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](https://claude.ai/chat/LICENSE)
[![VS Code](https://img.shields.io/badge/VS%20Code-Extension-007ACC?style=flat-square&logo=visual-studio-code)](https://zxkiidev.github.io/Iridium-Language/extension)
[![Docs](https://img.shields.io/badge/docs-online-purple?style=flat-square)](https://zxkiidev.github.io/Iridium-Language/docs)

</div>
---




---

Iridium is a hybrid-typed language designed for backend development and data science. It offers the simplicity of a high-level language with native constructs for building HTTP APIs, handling databases, working with tensors, and writing resilient logic — without installing any external libraries.

```iridium
// A complete REST endpoint in a few lines
db.sqlite("app.db")

route "/hello/<name>" => "GET":
    return jsonify({message: "Hello, {name}!", ok: true})
end

serve(8080)
```

---

## Why Iridium?

Most languages make you choose between **speed of development** and  **production robustness** . Iridium proposes a third path:

* **Native resilience** — The Sponge operator (`~>`) absorbs failures inline, no try-catch chains needed.
* **AI out-of-the-box** — Tensor types, vectorized math, and the `ia` inference object are part of the core, not a dependency.
* **Secure by design** — The `secure:` block encrypts data in transit and wipes secrets from RAM automatically.
* **Backend-first syntax** — HTTP routes, database queries, and environment loading are first-class grammar, not library calls.

---

## Features

| Feature                                                 | Status |
| ------------------------------------------------------- | ------ |
| Hybrid typing (`var`/`const`/ strict)               | ✅ V1  |
| Sponge operator `~>`(inline fallback)                 | ✅ V1  |
| Native HTTP server (`route`+`serve`)                | ✅ V1  |
| MySQL & SQLite built-in                                 | ✅ V1  |
| Classes and objects                                     | ✅ V1  |
| `secure:`block (encryption + memory wipe)             | ✅ V1  |
| Tensor type & vectorized math                           | ✅ V1  |
| `env`loader for `.env`files                         | ✅ V1  |
| Password hashing (`hash_password`/`check_password`) | ✅ V1  |
| VS Code extension (syntax + autocomplete)               | ✅ V1  |
| Bytecode compiler (`iricc`)                           | 🔵 V2  |
| Package manager (`iripkg`)                            | 🔵 V2  |
| Native LLVM compilation                                 | 🟣 V3  |
| GPU support (CUDA/ROCm)                                 | 🟣 V3  |

---

## Quick Look

**Variables & types**

```iridium
var name = "Zadquiel"          // dynamic
var score: float = 0.98        // strict
const THRESHOLD: float = 0.85  // immutable
```

**Resilience with Sponge**

```iridium
// If the API call fails, fall back to "127.0.0.1"
var host = api.getHost() ~> "127.0.0.1"

// Safe division — no crash on zero
var ratio = (points / total) ~> 0.0
```

**HTTP API**

```iridium
db.config("localhost", "root", "", "mydb")

route "/users/<id>" => "GET":
    var user = db.query_one("SELECT * FROM users WHERE id = ?", id)
    return jsonify({name: user.name, email: user.email})
end

route "/login" => "POST":
    var user = db.query_one("SELECT * FROM users WHERE name = ?", body.name)
    var valid = check_password(user.password, body.password)
    return jsonify({authenticated: valid})
end

serve(8080)
```

**Classes**

```iridium
class User():
    var name = ""
    var exp  = 0

    function greet():
        out "Hi, I'm {name} with {exp} points"
    end

    function gain_exp(amount):
        exp += amount
    end
end

var u = User()
u.name = "Ana"
u.gain_exp(50)
u.greet()  // → "Hi, I'm Ana with 50 points"
```

**Secure block**

```iridium
secure:
    var password = "secret_key"
    db.save(password)       // auto-encrypted at rest
    out "Saving: {password}" // prints ********
end
```

---

## Download

Iridium is distributed as a ready-to-run binary. No build tools required.

**→ [GitHub Releases](https://github.com/zxkiidev/Iridium-Language/releases)** — download the latest `.zip` for Windows x64, extract it, and add the folder to your PATH.

**→ [Official Website](https://zxkiidev.github.io/Iridium-Language/downloads)** — installers and changelogs for every version.

After installation, verify it works:

```
iridium --version
Iridium Engine v1.0 | Build: 2026
```

---

## VS Code Extension

The official extension provides syntax highlighting, autocomplete for all keywords and built-in objects (`db`, `ia`, `math`), and snippets for common structures like `iroute`, `irclass`, and `irapi`.

**→ [Get the Extension](https://zxkiidev.github.io/Iridium-Language/extension)**

---

## Documentation

Full reference at **[zxkiidev.github.io/Iridium-Language/docs](https://zxkiidev.github.io/Iridium-Language/docs)**

Topics covered: Hybrid Typing · Sponge Operator · I/O · Collections · Control Flow · Memory · Security · Networking · Databases · Tensors · AI Integration · Classes · Backend Optimization · VS Code · Error Reference · Roadmap · Glossary

---

## Roadmap

* **V2** — Own bytecode compiler, stack VM in C, package manager, multi-file projects, vector database support
* **V3** — LLVM native compilation, manual memory management, distributed AI training, GPU support

Full details in [docs/roadmap](https://zxkiidev.github.io/Iridium-Language/docs/docs-roadmap.html).

---

## License

MIT © 2026 [zxkiidev](https://github.com/zxkiidev)
