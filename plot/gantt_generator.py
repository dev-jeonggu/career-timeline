from utils.font_config import set_korean_font
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import textwrap
import warnings
import os
from datetime import datetime


def generate_final_layout_gantt(df, output_path="output/career_gantt_final.png"):
    set_korean_font()

    today = datetime.today()
    df = df.copy()
    df["ongoing"] = df["end"].astype(str).str.strip().str.lower() == "present"
    df["end"] = df["end"].apply(
        lambda x: today.strftime("%Y-%m-%d") if str(x).strip().lower() == "present" else x
    )

    df["start"]    = pd.to_datetime(df["start"])
    df["end"]      = pd.to_datetime(df["end"])
    df["duration"] = (df["end"] - df["start"]).dt.days
    df["year"]     = df["start"].dt.year

    category_colors = {
        "교육": "#90be6d",
        "근무": "#577590",
        "자격증": "#f9c74f",
        "수상":  "#ffcce5"
    }

    min_year   = df["start"].dt.year.min()
    max_year   = max(df["start"].dt.year.max(), df["end"].dt.year.max())
    full_years = range(min_year, max_year + 2)

    year_counts = df["year"].value_counts().to_dict()

    # 이벤트 있는 연도 넓게, 없는 연도 좁게
    gap_event = 0.9
    gap_empty = 0.3
    year_positions = {}
    cur_pos = 0
    for year in full_years:
        year_positions[year] = cur_pos
        cur_pos += gap_event if year_counts.get(year, 0) > 0 else gap_empty

    def year_to_num(dt):
        y    = dt.year
        frac = (dt - datetime(y, 1, 1)).days / 365.0
        pos  = year_positions.get(y, cur_pos)
        nxt  = year_positions.get(y + 1, pos + gap_event)
        return pos + frac * (nxt - pos)

    # ── 레이아웃 상수 ──────────────────────────────────────────
    bar_y      = 0.8
    bar_height = 0.35
    layer_gap  = 0.42
    MAX_DAY_LAYERS = 4

    def calculate_layers(df):
        """실제 날짜 겹침으로 레이어 결정."""
        items = df[df["duration"] > 1].copy().sort_values("start")
        if items.empty:
            return {}
        layers   = {}
        occupied = []   # (start, end, layer)
        MAX_L = 5
        for idx, row in items.iterrows():
            s, e = row["start"], row["end"]
            layer = 0
            while layer < MAX_L:
                if not any(s < oe and e > os and l == layer
                           for os, oe, l in occupied):
                    break
                layer += 1
            layers[idx] = min(layer, MAX_L - 1)
            occupied.append((s, e, layers[idx]))
        return layers

    duration_layers = calculate_layers(df)

    # ── 축 경계 & 피겨 크기 ────────────────────────────────────
    x_min = year_to_num(df["start"].min())
    x_max = year_to_num(df["end"].max())
    start_line = x_min - 0.3
    end_line   = x_max + 0.4

    max_dur_layer = max(duration_layers.values()) if duration_layers else 0
    max_bar_top   = bar_y + max_dur_layer * (bar_height + 0.2) + bar_height / 2 + 0.4
    max_pt_top    = 1.75 + (MAX_DAY_LAYERS - 1) * layer_gap + 0.4
    y_top = max(max_bar_top, max_pt_top) + 0.5

    x_span     = end_line - start_line
    fig_width  = max(16, x_span * 2.6)
    fig_height = max(4.0, y_top * 2.0)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # ── 타임라인 배경선 & 연도 레이블 ─────────────────────────
    ax.add_patch(patches.Rectangle(
        (start_line, 0), end_line - start_line, 0.15,
        facecolor="#333333", zorder=0
    ))
    for year in full_years:
        if year in year_positions:
            ax.text(year_positions[year], 0.075, str(year),
                    ha="center", va="center", color="white", fontsize=14)

    # ── x 근접 기반 point 이벤트 레이어 ──────────────────────
    placed_pts = []   # (x, layer)
    MIN_X_GAP  = 0.55

    for row in df.itertuples():
        color   = category_colors.get(row.category, "#cccccc")
        raw_lbl = str(getattr(row, "label", ""))
        label   = raw_lbl.replace("\\n", "\n") if "\\n" in raw_lbl \
                  else "\n".join(textwrap.wrap(raw_lbl, width=15))

        if row.duration <= 1:
            x      = year_to_num(row.start)
            nearby = {pl for px, pl in placed_pts if abs(px - x) < MIN_X_GAP}
            cur_l  = 0
            while cur_l in nearby:
                cur_l += 1
            cur_l = cur_l % MAX_DAY_LAYERS
            placed_pts.append((x, cur_l))

            ly = 1.75 + cur_l * layer_gap
            ax.text(x, 0.19, "▼", ha="center", va="center", fontsize=20, color=color)
            ax.plot([x, x], [0.17, ly - 0.05], linestyle=":", color=color, linewidth=2)
            ax.text(x, ly,        f"({row.start.strftime('%Y.%m.%d')})",
                    ha="center", va="bottom", fontsize=13)
            ax.text(x, ly + 0.08, label,
                    ha="center", va="bottom", fontsize=15)

        else:
            # 날짜 기반 바 (연도 레이블과 정렬)
            x       = year_to_num(row.start)
            x_end   = year_to_num(row.end)
            width   = x_end - x
            lyr     = duration_layers.get(row.Index, 0)
            cur_y   = bar_y + lyr * (bar_height + 0.2)
            cx      = (x + x_end) / 2

            ax.add_patch(patches.FancyBboxPatch(
                (x, cur_y - bar_height / 2), width, bar_height,
                boxstyle="round,pad=0.02", facecolor=color, edgecolor="none"
            ))

            date_lbl = (f"({row.start.strftime('%Y.%m')}–현재)"
                        if row.ongoing
                        else f"({row.start.strftime('%Y.%m')}–{row.end.strftime('%Y.%m')})")

            ax.text(cx, cur_y,       label,    ha="center", va="center", fontsize=17, weight="bold")
            ax.text(cx, cur_y + 0.2, date_lbl, ha="center", va="bottom", fontsize=11)

    ax.set_xlim(start_line, end_line)
    ax.set_ylim(-0.1, y_top)
    ax.axis("off")

    legend_elements = [patches.Patch(facecolor=c, label=cat)
                       for cat, c in category_colors.items()
                       if cat in df["category"].values]
    if legend_elements:
        ax.legend(handles=legend_elements, loc="upper right",
                  bbox_to_anchor=(0.99, 0.95), fontsize=16)

    fig.subplots_adjust(left=0, right=1, top=0.95, bottom=0)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        plt.savefig(output_path, dpi=200, facecolor="white", edgecolor="none",
                    format="png", pil_kwargs={"optimize": True})
    plt.close()
    print(f"✅ 간트 차트 저장 완료 → {output_path}")
    return output_path
