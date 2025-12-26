def save_langgraph_png1(app, output_file: str = "langgraph_graph.png", prefer_local: bool = True) -> str:
    """
    Сохраняет диаграмму LangGraph в PNG.

    app: результат builder.compile(...)
    prefer_local=True -> рендер локально через PYPPETEER (без Mermaid.ink).
    """
    from pathlib import Path

    g = app.get_graph()
    out_path = Path(output_file)

    draw_kwargs = {}
    if prefer_local:
        try:
            from langchain_core.runnables.graph import MermaidDrawMethod  # type: ignore
            draw_kwargs["draw_method"] = MermaidDrawMethod.PYPPETEER
        except Exception as e:
            raise RuntimeError(
                "Локальный рендер требует langchain_core и pyppeteer. "
                "Установи pyppeteer или вызови save_langgraph_png(..., prefer_local=False)."
            ) from e

    # В некоторых версиях draw_mermaid_png умеет сам писать файл через output_file_path
    try:
        g.draw_mermaid_png(output_file_path=str(out_path), **draw_kwargs)
        if out_path.exists():
            return str(out_path)
    except TypeError:
        # нет параметра output_file_path -> пишем байты сами
        pass

    png_bytes = g.draw_mermaid_png(**draw_kwargs)
    out_path.write_bytes(png_bytes)
    return str(out_path)

def save_langgraph_png2(app, output_file: str = "langgraph_graph.png") -> str:
    """
    Полностью локально сохраняет граф в PNG (без pyppeteer/Chromium/внешних сервисов).
    Требует: pip install networkx matplotlib
    """
    from pathlib import Path

    try:
        import networkx as nx
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise RuntimeError("Нужно установить зависимости: pip install networkx matplotlib") from e

    g = app.get_graph()

    # ---- извлекаем узлы ----
    nodes = []
    raw_nodes = getattr(g, "nodes", None)
    if isinstance(raw_nodes, dict):
        nodes = [str(k) for k in raw_nodes.keys()]
    elif isinstance(raw_nodes, (list, tuple, set)):
        nodes = [str(x) for x in raw_nodes]
    else:
        nodes = []

    # ---- извлекаем ребра ----
    edges = []
    raw_edges = getattr(g, "edges", None) or []
    for e in raw_edges:
        s = t = None

        if isinstance(e, tuple) and len(e) >= 2:
            s, t = e[0], e[1]
        else:
            # разные версии могут называть поля по-разному
            s = getattr(e, "source", None) or getattr(e, "start", None) or getattr(e, "from_", None) or getattr(e, "from_node", None)
            t = getattr(e, "target", None) or getattr(e, "end", None) or getattr(e, "to", None) or getattr(e, "to_node", None)

        if s is None or t is None:
            continue

        s, t = str(s), str(t)
        edges.append((s, t))
        if s not in nodes:
            nodes.append(s)
        if t not in nodes:
            nodes.append(t)

    # ---- рисуем ----
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    # фиксируем seed для стабильной раскладки между запусками
    pos = nx.spring_layout(G, seed=42)

    plt.figure(figsize=(14, 8))
    nx.draw_networkx(G, pos=pos, with_labels=True, arrows=True)
    plt.axis("off")

    out = Path(output_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()

    return str(out)