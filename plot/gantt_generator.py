from utils.font_config import set_korean_font
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.dates as mdates
import pandas as pd
import textwrap
import warnings
import os
from datetime import datetime


def generate_final_layout_gantt(df, output_path="output/career_gantt_final.png"):
    set_korean_font()

    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    df["duration"] = (df["end"] - df["start"]).dt.days
    df["year"] = df["start"].dt.year

    category_colors = {
        "교육": "#90be6d",
        "근무": "#577590",
        "자격증": "#f9c74f",
        "수상": "#ffcce5"
    }

    # 연도 범위: 시작년도보다 한 해 앞부터, 종료년도보다 한 해 뒤까지
    full_years = range(df["year"].min(), df["year"].max() + 2)
    year_counts = df["year"].value_counts().to_dict()

    base_gap = 1.0
    year_positions = {}
    current_pos = 0
    for year in full_years:
        count = year_counts.get(year, 0)
        year_positions[year] = current_pos
        if count <= 3:
            current_pos += base_gap * 0.3
        else:
            current_pos += base_gap

    fig, ax = plt.subplots(figsize=(32, 10))
    bar_y = 0.8
    bar_height = 0.35
    arrow_height = 0.15
    day_event_offsets = {}
    layer_gap = 0.25

    def year_to_num(dt):
        y = dt.year
        frac = (dt - datetime(y, 1, 1)).days / 365.0
        return year_positions.get(y, 0) + frac * (year_positions.get(y + 1, year_positions[y] + base_gap) - year_positions[y])

    # 하단 타임라인 배경선 추가
    start_line = min(year_positions.values()) - 0.1
    end_line = max(year_positions.values()) + 0.1
    ax.add_patch(patches.Rectangle(
        (start_line, 0),
        end_line - start_line,
        0.15,
        facecolor="#333333",
        zorder=0
    ))

    for year in full_years:
        if year in year_positions:
            ax.text(year_positions[year], 0.075, str(year), ha='center', va='center', color='white', fontsize=14)

    def calculate_layer_for_duration_items(df):
        duration_items = df[df["duration"] > 1].copy()
        if len(duration_items) == 0:
            return {}
        duration_items = duration_items.sort_values('start')
        layers = {}
        occupied_layers = []
        MAX_LAYERS = 5
        for original_idx, row in duration_items.iterrows():
            start_date, end_date = row['start'], row['end']
            current_layer = 0
            while current_layer < MAX_LAYERS:
                overlap = any(start_date < e and end_date > s and l == current_layer
                              for s, e, l in occupied_layers)
                if not overlap:
                    break
                current_layer += 1
            if current_layer >= MAX_LAYERS:
                current_layer = MAX_LAYERS - 1
            layers[original_idx] = current_layer
            occupied_layers.append((start_date, end_date, current_layer))
        return layers

    duration_layers = calculate_layer_for_duration_items(df)

    for row in df.itertuples():
        color = category_colors.get(row.category, "#cccccc")
        raw_label = str(getattr(row, 'label', '라벨 없음'))
        label = raw_label.replace('\\n', '\n') if '\\n' in raw_label else "\n".join(textwrap.wrap(raw_label, width=15))

        if row.duration <= 1:
            x = year_to_num(row.start)
            date_key = row.start.date()
            current_layer = day_event_offsets.get(date_key, 0)
            while current_layer in day_event_offsets.values():
                current_layer += 1
            day_event_offsets[date_key] = current_layer
            MAX_DAY_LAYERS = 4
            if current_layer >= MAX_DAY_LAYERS:
                current_layer = current_layer % MAX_DAY_LAYERS
            layer_y = 1.5 + current_layer * layer_gap
            ax.text(x, 0.19, '▼', ha='center', va='center', fontsize=20, color=color)
            ax.plot([x, x], [0.17, layer_y - 0.05], linestyle=":", color=color, linewidth=2)
            ax.text(x, layer_y, f"({row.start.strftime('%Y.%m.%d')})", ha='center', va='bottom', fontsize=15)
            ax.text(x, layer_y + 0.08, label, ha='center', va='bottom', fontsize=17)
        else:
            x = year_to_num(row.start)
            x_end = year_to_num(row.end)
            width = x_end - x
            item_layer = duration_layers.get(row.Index, 0)
            current_bar_y = bar_y + item_layer * (bar_height + 0.2)
            ax.add_patch(patches.FancyBboxPatch(
                (x, current_bar_y - bar_height / 2),
                width, bar_height,
                boxstyle="round,pad=0.02",
                facecolor=color,
                edgecolor='none'
            ))
            center_x = (x + x_end) / 2
            ax.text(center_x, current_bar_y, label, ha='center', va='center', fontsize=17, weight='bold')
            ax.text(center_x, current_bar_y + 0.2, f"({row.start.strftime('%Y.%m')}–{row.end.strftime('%Y.%m')})", ha='center', va='bottom', fontsize=15)

    ax.set_xlim(start_line, end_line)
    ax.set_ylim(-0.1, 4.0)
    ax.axis('off')

    legend_elements = [patches.Patch(facecolor=color, label=category)
                       for category, color in category_colors.items()
                       if category in df['category'].values]
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.99, 0.95), fontsize=16)

    fig.subplots_adjust(left=0, right=1, top=0.95, bottom=0)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        plt.savefig(output_path, dpi=600, facecolor='white', edgecolor='none', format='png', pil_kwargs={'optimize': True})
    plt.close()
    print(f"✅ 간트 차트 저장 완료 → {output_path}")
    return output_path