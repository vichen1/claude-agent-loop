from importlib import import_module

OPTIONAL = ["swe", "ml"]


def load(names):
    modules = [import_module("tools.core")]
    for n in names:
        if n not in OPTIONAL:
            raise ValueError(f"Unknown toolset '{n}'. Available: {OPTIONAL}")
        modules.append(import_module(f"tools.{n}"))

    schemas, owner = [], {}
    for mod in modules:
        for schema in mod.TOOLS:
            schemas.append(schema)
            owner[schema["name"]] = mod

    def dispatch(name, tool_input):
        mod = owner.get(name)
        if mod is None:
            return f"Unknown tool: {name}"
        return mod.execute_tool(name, tool_input)

    return schemas, dispatch
