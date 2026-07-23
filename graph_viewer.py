import os
import glob
import re
import networkx as nx
import matplotlib.pyplot as plt

def show_neural_graph(vault_path="RNT_Vault"):
    """
    Сканирует все Markdown файлы в хранилище, парсит связи [[Название]] 
    и визуализирует граф нейронной сети RNT.
    """
    G = nx.Graph()
    md_files = glob.glob(os.path.join(vault_path, "*.md"))
    
    if not md_files:
        print("[Graph] Нет файлов для построения графа.")
        return

    # 1. Собираем узлы и связи
    for file_path in md_files:
        filename = os.path.basename(file_path).replace(".md", "")
        G.add_node(filename)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Ищем все ссылки формата [[ИмяЗаметки]]
            links = re.findall(r"\[\[(.*?)\]\]", content)
            for target in links:
                if target != filename:
                    G.add_edge(filename, target)
        except Exception as e:
            print(f"[Graph Ошибка] Не удалось прочитать {filename}: {e}")

    # 2. Настройка стиля (RNT Cyber-Minimalism: Black & Neon Blue)
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(11, 7), facecolor='#000000')
    ax.set_facecolor('#000000')
    
    # Меняем заголовок окна
    try:
        fig.canvas.manager.set_window_title("RNT Notes - Neural Graph Matrix")
    except Exception:
        pass

    # Расчет физики связей (Spring Layout)
    pos = nx.spring_layout(G, k=0.6, seed=42)

    # Отрисовка линий связей (Неоново-синие неоновые нити)
    nx.draw_networkx_edges(
        G, pos, ax=ax, 
        edge_color="#00D4FF", alpha=0.5, width=1.8
    )

    # Отрисовка узлов (Светящиеся ядерные точки)
    nx.draw_networkx_nodes(
        G, pos, ax=ax, 
        node_color="#00D4FF", node_size=450, alpha=0.85
    )

    # Подписи файлов (Консольный шрифт)
    nx.draw_networkx_labels(
        G, pos, ax=ax, 
        font_color="#FFFFFF", font_size=10, font_family="Consolas",
        verticalalignment="bottom"
    )

    plt.title("RNT NEURAL GRAPH MATRIX", color="#00D4FF", fontsize=14, fontweight="bold", pad=20, fontfamily="Consolas")
    plt.axis('off')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    show_neural_graph()