"""Pure-Python compiler for FSCSS (Figured Shorthand CSS).

Supports the FSCSS syntax used across this project:
$variables (with/without the trailing ! marker), property shorthands
and aliases, axis spacing (px/py/mx/my/gap-x/...), size/radius helpers,
@fun style stores, @define parameterized blocks with @use(), the %2()/%3()
group shorthand, rpt(), && nesting, and plain CSS passthrough.
"""

import re

MULTI_PROP = {
    "size": ("width", "height"),
    "min-size": ("min-width", "min-height"),
    "max-size": ("max-width", "max-height"),
}

AXIS_PAIRS = {
    "mx": ("margin-left", "margin-right"),
    "my": ("margin-top", "margin-bottom"),
    "px": ("padding-left", "padding-right"),
    "py": ("padding-top", "padding-bottom"),
    "gap-x": ("column-gap", "row-gap"),
    "gap-y": ("row-gap", "column-gap"),
    "inset-x": ("left", "right"),
    "inset-y": ("top", "bottom"),
    "scroll-mx": ("scroll-margin-left", "scroll-margin-right"),
    "scroll-my": ("scroll-margin-top", "scroll-margin-bottom"),
    "scroll-px": ("scroll-padding-left", "scroll-padding-right"),
    "scroll-py": ("scroll-padding-top", "scroll-padding-bottom"),
}

BORDER_AXES = {
    "border-x": ("border-left", "border-right"),
    "border-y": ("border-top", "border-bottom"),
    "border-t": ("border-top",),
    "border-b": ("border-bottom",),
    "border-l": ("border-left",),
    "border-r": ("border-right",),
    "bw-x": ("border-width", "border-width"),
}

SIDE_PROPS = {
    "padding": {"top": "padding-top", "bottom": "padding-bottom",
                "left": "padding-left", "right": "padding-right",
                "block-start": "padding-top", "block-end": "padding-bottom",
                "inline-start": "padding-left", "inline-end": "padding-right"},
    "margin": {"top": "margin-top", "bottom": "margin-bottom",
               "left": "margin-left", "right": "margin-right",
               "block-start": "margin-top", "block-end": "margin-bottom",
               "inline-start": "margin-left", "inline-end": "margin-right"},
    "inset": {"top": "top", "bottom": "bottom", "left": "left", "right": "right"},
    "border-width": {"top": "border-top-width", "bottom": "border-bottom-width",
                     "left": "border-left-width", "right": "border-right-width"},
    "border-style": {"top": "border-top-style", "bottom": "border-bottom-style",
                     "left": "border-left-style", "right": "border-right-style"},
    "border-color": {"top": "border-top-color", "bottom": "border-bottom-color",
                     "left": "border-left-color", "right": "border-right-color"},
}

RADIUS_CORNERS = {
    "rounded-t": ("border-top-left-radius", "border-top-right-radius"),
    "rounded-b": ("border-bottom-left-radius", "border-bottom-right-radius"),
    "rounded-l": ("border-top-left-radius", "border-bottom-left-radius"),
    "rounded-r": ("border-top-right-radius", "border-bottom-right-radius"),
    "rounded-tl": ("border-top-left-radius",),
    "rounded-tr": ("border-top-right-radius",),
    "rounded-bl": ("border-bottom-left-radius",),
    "rounded-br": ("border-bottom-right-radius",),
}

ALIASES = {
    "m": "margin", "mt": "margin-top", "mb": "margin-bottom",
    "ml": "margin-left", "mr": "margin-right",
    "p": "padding", "pt": "padding-top", "pb": "padding-bottom",
    "pl": "padding-left", "pr": "padding-right",
    "fs": "font-size", "fw": "font-weight", "ff": "font-family",
    "lh": "line-height", "ls": "letter-spacing",
    "ta": "text-align", "td": "text-decoration", "tt": "text-transform",
    "ws": "white-space", "tsh": "text-shadow",
    "ov": "overflow", "ovx": "overflow-x", "ovy": "overflow-y",
    "z": "z-index", "op": "opacity", "cur": "cursor",
    "pe": "pointer-events", "us": "user-select", "pos": "position",
    "jc": "justify-content", "ai": "align-items", "ac": "align-content",
    "ji": "justify-items", "js": "justify-self", "as": "align-self",
    "pi": "place-items", "fdir": "flex-direction", "fwrap": "flex-wrap",
    "grow": "flex-grow", "shrink": "flex-shrink", "basis": "flex-basis",
    "trans": "transition", "anim": "animation", "tf": "transform",
    "fil": "filter", "shadow": "box-shadow", "aspect": "aspect-ratio",
    "obj-fit": "object-fit", "obj-pos": "object-position",
    "w": "width", "h": "height",
    "min-w": "min-width", "max-w": "max-width",
    "min-h": "min-height", "max-h": "max-height",
    "bg": "background",
    "bg-color": "background-color", "bg-image": "background-image",
    "bg-repeat": "background-repeat", "bg-pos": "background-position",
    "bg-attachment": "background-attachment", "bg-clip": "background-clip",
    "bg-origin": "background-origin", "bg-size": "background-size",
    "bg-x": "background-position-x", "bg-y": "background-position-y",
    "bg-size-x": "background-size", "bg-size-y": "background-size",
    "bw": "border-width", "bs": "border-style", "bc": "border-color",
    "rounded": "border-radius", "radius": "border-radius",
    "radius-top": "border-top-left-radius",
    "radius-bottom": "border-bottom-left-radius",
}

SIDES_BW = {"bw-t": "border-top-width", "bw-b": "border-bottom-width",
            "bw-l": "border-left-width", "bw-r": "border-right-width"}
SIDES_BS = {"bs-t": "border-top-style", "bs-b": "border-bottom-style",
            "bs-l": "border-left-style", "bs-r": "border-right-style"}
SIDES_BC = {"bc-t": "border-top-color", "bc-b": "border-bottom-color",
            "bc-l": "border-left-color", "bc-r": "border-right-color"}

VAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_-]*)")
AT_RULES_STATIC = {"@import", "@charset", "@namespace", "@font-face"}
AT_RULES_BLOCK = {"media", "supports", "document", "layer", "container"}
AT_RULES_KEYFRAMES = {"keyframes"}


def _expand_value(value, vars_):
    value = value.strip()
    while True:
        m = VAR_RE.search(value)
        if not m:
            break
        name = m.group(1)
        if name not in vars_:
            value = value[:m.start()] + value[m.end():]
            continue
        start = m.end()
        while start < len(value) and value[start] in " \t":
            start += 1
        if start < len(value) and value[start] == "!" and not value.startswith("!important", start):
            start += 1
        replacement = _expand_value(vars_[name], vars_)
        value = value[:m.start()] + replacement + value[start:]
    value = value.replace("@@", "@")
    value = _apply_rpt(value)
    value = _strip_bang(value)
    return value.strip()


def _strip_bang(value):
    value = value.rstrip()
    if value.endswith("!") and not value.endswith("!important"):
        value = value[:-1].rstrip()
    value = value.replace(" !important", "!important")
    return value


def _apply_rpt(value):
    def repl(m):
        count = int(m.group(1))
        payload = m.group(2)
        text = ""
        for _ in range(count):
            text += payload
        return text

    return re.sub(r"rpt\(\s*(\d+)\s*,\s*(['\"])(.*?)\2\s*\)", repl, value, flags=re.S)


def _split_value(value):
    parts = re.split(r"\s+", value.strip())
    parts = [p for p in parts if p]
    return parts


def _shorthand_expand(prop, value, vars_):
    value = _expand_value(value, vars_)
    prop = prop.strip().lower()

    if prop in MULTI_PROP:
        vals = _split_value(value)
        if len(vals) >= 2:
            a, b = MULTI_PROP[prop]
            return [(a, vals[0]), (b, vals[1])]
        a, b = MULTI_PROP[prop]
        return [(a, vals[0] if vals else ""), (b, vals[0] if vals else "")]

    if prop in AXIS_PAIRS:
        vals = _split_value(value)
        if len(vals) >= 2:
            left, right = AXIS_PAIRS[prop]
            return [(left, vals[0]), (right, vals[-1])]
        left, right = AXIS_PAIRS[prop]
        return [(left, value), (right, value)]

    if prop in BORDER_AXES:
        outs = []
        for side in BORDER_AXES[prop]:
            outs.append((side, value))
        return outs

    if prop in RADIUS_CORNERS:
        outs = []
        for corner in RADIUS_CORNERS[prop]:
            outs.append((corner, value))
        return outs

    if prop.startswith("rounded-") or prop.startswith("radius-"):
        return [(prop.replace("rounded-", "border-top-left-")
                     .replace("radius-", "border-top-left-"), value)]

    if prop == "stack" or prop == "hstack":
        direction = "row" if prop == "hstack" else "column"
        decls = [("display", "flex"), ("flex-direction", direction)]
        if value:
            decls.append(("gap", value))
        return decls

    if prop == "center":
        if value == "x":
            return [("justify-content", "center")]
        if value == "y":
            return [("align-items", "center")]
        return [("display", "grid"), ("place-items", "center")]

    if prop == "fill":
        pos = "fixed" if value == "fixed" else "absolute"
        return [("position", pos), ("inset", "0")]

    if prop == "abs-center":
        return [("position", "absolute"), ("inset", "0"), ("margin", "auto")]

    if prop == "truncate":
        return [("overflow", "hidden"), ("white-space", "nowrap"),
                ("text-overflow", "ellipsis")]

    if prop == "line-clamp":
        n = _split_value(value)[0] if value else "2"
        return [("display", "-webkit-box"), ("-webkit-box-orient", "vertical"),
                ("-webkit-line-clamp", n), ("overflow", "hidden")]

    if prop == "glass":
        blur = value or "10px"
        return [("backdrop-filter", "blur(" + blur + ")"),
                ("-webkit-backdrop-filter", "blur(" + blur + ")")]

    if prop == "ring":
        width = value or "3px"
        return [("box-shadow", "0 0 0 " + width + " rgba(124, 92, 255, 0.35)")]

    if prop == "auto-fit":
        mini = _split_value(value)[0] if value else "minmax(240px, 1fr)"
        grid = "repeat(auto-fit, " + mini + ")"
        return [("display", "grid"), ("grid-template-columns", grid)]

    if prop in ("cols", "rows"):
        n = _split_value(value)[0] if value else "1"
        if n.isdigit():
            n = "repeat(" + n + ", 1fr)"
        axis = "grid-template-columns" if prop == "cols" else "grid-template-rows"
        return [("display", "grid"), (axis, n)]

    if prop in SIDES_BW:
        return [(SIDES_BW[prop], value)]
    if prop in SIDES_BS:
        return [(SIDES_BS[prop], value)]
    if prop in SIDES_BC:
        return [(SIDES_BC[prop], value)]

    if prop in ALIASES:
        return [(ALIASES[prop], value)]

    if prop == "place-x":
        return [("justify-content", value), ("justify-items", value)]
    if prop == "place-y":
        return [("align-content", value), ("align-items", value)]
    if prop == "origin-x":
        return [("transform-origin", value + " 0")]
    if prop == "origin-y":
        return [("transform-origin", "0 " + value)]

    return [(prop, value)]


def _split_decl(raw):
    i, n, q = 0, len(raw), None
    depth = 0
    while i < n:
        ch = raw[i]
        if q:
            if ch == "\\":
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == ":" and depth == 0:
            prop = raw[:i].strip()
            value = raw[i + 1:].strip()
            return prop, value
        i += 1
    return raw.strip(), ""


def _parse_fun_name(raw):
    raw = raw.strip()
    if raw.startswith("@fun"):
        return raw[4:].strip()
    return raw.strip()


class Compiler:
    def __init__(self):
        self.stores = {}
        self.defines = {}

    def compile(self, source):
        self.stores = {}
        self.defines = {}
        return self._parse_scope(source, {}, top=True)

    def _parse_scope(self, text, vars_, top=False, indent=0):
        out = []
        vars_ = dict(vars_)
        i, n = 0, len(text)
        pad = "  " * indent
        while i < n:
            ch = text[i]
            if ch.isspace():
                i += 1
                continue
            if text.startswith("/*", i):
                end = text.find("*/", i + 2)
                i = n if end == -1 else end + 2
                continue
            if ch in ";}\n":
                i += 1
                continue

            j, q, depth = i, None, 0
            stmt_end = -1
            brace_idx = -1
            while j < n:
                c = text[j]
                if q:
                    if c == "\\":
                        j += 2
                        continue
                    if c == q:
                        q = None
                elif c in "'\"":
                    q = c
                elif c in "([":
                    depth += 1
                elif c in ")]":
                    depth -= 1
                elif depth == 0 and c == "{":
                    brace_idx = j
                    break
                elif depth == 0 and c == ";":
                    stmt_end = j
                    break
                j += 1

            if brace_idx != -1:
                raw_selector = text[i:brace_idx].strip()
                open_idx = brace_idx
                close_idx = self._find_matching(text, open_idx)
                inner = text[open_idx + 1:close_idx] if close_idx != -1 else ""
                i = n if close_idx == -1 else close_idx + 1
                self._handle_selector(raw_selector, inner, vars_, out, pad, indent, top)
                continue

            if stmt_end != -1:
                raw = text[i:stmt_end].strip()
                i = stmt_end + 1
                self._handle_statement(raw, vars_, out, pad)
                continue

            if stmt_end == -1 and brace_idx == -1:
                rest = text[i:].strip()
                if rest:
                    self._handle_statement(rest, vars_, out, pad)
                    i = n
                else:
                    i = n

        return "\n".join(out)

    def _find_matching(self, text, open_idx):
        depth, i, q = 0, open_idx, None
        n = len(text)
        while i < n:
            c = text[i]
            if q:
                if c == "\\":
                    i += 2
                    continue
                if c == q:
                    q = None
            elif c in "'\"":
                q = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    def _handle_selector(self, selector, inner, vars_, out, pad, indent, top):
        sel = selector.strip()
        first = sel.split("{", 1)[0].strip()
        lname = first.lower()

        name = re.match(r"@([a-zA-Z-]+)", lname)

        if name:
            at = name.group(1)
            rest = first.replace("@" + at, "", 1).strip()
            compiled = self._parse_scope(inner, vars_, indent=indent)
            if at in AT_RULES_KEYFRAMES:
                out.append("@" + at + " " + rest + " {")
                out.append(compiled or "  /* empty */")
                out.append("}")
            elif at in AT_RULES_BLOCK or at in AT_RULES_STATIC:
                out.append("@" + at + " " + rest + " {")
                if compiled:
                    out.append(compiled)
                out.append("}")
            elif at == "fun":
                name_ = _parse_fun_name(rest)
                decls = self._parse_declarations(inner, vars_)
                self.stores[name_.lstrip(".")] = decls
            elif at == "define":
                m = re.match(r"([A-Za-z_][\w-]*)\s*\((.*?)\)", rest)
                if m:
                    name_ = m.group(1)
                    params = [p.strip() for p in m.group(2).split(",") if p.strip()]
                    self.defines[name_] = (params, inner)
            return

        compiled = self._parse_scope(inner, vars_, indent=indent)
        if not compiled:
            return
        out.append(pad + sel + " {")
        out.append(compiled)
        out.append(pad + "}")

    def _handle_statement(self, raw, vars_, out, pad):
        if not raw:
            return

        vm = re.match(r"^\$([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", raw)
        if vm:
            vars_[vm.group(1)] = vm.group(2)
            return

        side = re.match(
            r"^(top|bottom|left|right|block-start|block-end|inline-start|inline-end)\s*\|", raw)
        if side:
            side_name = side.group(1)
            rest = raw[side.end():]
            inner = rest.rsplit("|", 1)[0] if "|" in rest else rest
            for decl in self._parse_declarations(inner, vars_):
                prop, value = decl
                mapped = SIDE_PROPS.get(prop, {}).get(side_name)
                if mapped:
                    out.append(pad + mapped + ": " + value + ";")
            return

        if raw.startswith("@fun") or raw.startswith("@"):
            m = re.match(r"^@([A-Za-z_][\w-]*)\.?([\w.-]*)", raw)
            if m:
                kind = m.group(1)
                name = m.group(2) or raw.split(kind, 1)[1].lstrip(".")
                name = name.strip()
                if kind == "fun" and name:
                    decls = self.stores.get(name.lstrip("."))
                    if decls:
                        for prop, value in decls:
                            out.append(pad + prop + ": " + value + ";")
                return
            return

        prop, value = _split_decl(raw)
        if not prop:
            return

        for css_prop, css_value in _shorthand_expand(prop, value, vars_):
            out.append(pad + css_prop + ": " + css_value + ";")

    def _parse_declarations(self, text, vars_):
        inner = self._parse_scope(text, vars_, top=False)
        decls = []
        for line in inner.splitlines():
            line = line.strip()
            if ":" in line and line.endswith(";"):
                prop, value = _split_decl(line[:-1])
                if prop and not prop.startswith("@"):
                    decls.append((prop, value))
        return decls


def compile_fscss(source):
    return Compiler().compile(source)