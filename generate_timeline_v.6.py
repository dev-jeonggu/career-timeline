import matplotlib
import matplotlib.font_manager as fm
import platform
import warnings

# 한글 폰트 설정 및 경고 숨기기
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

# 운영체제별 한글 폰트 설정
if platform.system() == 'Darwin':  # macOS
    matplotlib.rcParams['font.family'] = 'AppleGothic'
elif platform.system() == 'Linux':  # Ubuntu/Linux (GitHub Actions)
    # 사용 가능한 한글 폰트 찾기
    font_names = [font.name for font in fm.fontManager.ttflist]
    korean_fonts = ['NanumGothic', 'NanumBarunGothic', 'DejaVu Sans', 'Liberation Sans']

    selected_font = 'DejaVu Sans'  # 기본값
    for font in korean_fonts:
        if font in font_names:
            selected_font = font
            break

    matplotlib.rcParams['font.family'] = selected_font
    print(f"🔤 사용 폰트: {selected_font}")

# 마이너스 기호 문제 해결
matplotlib.rcParams['axes.unicode_minus'] = False

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.dates as mdates
import pandas as pd
import textwrap
import json

from datetime import datetime
import os

# JSON 데이터 로드
def load_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))

# 최종 Gantt 스타일 시각화 (텍스트 중앙 정렬, 줄바꿈 적용, 하루 위 화살표)
def generate_final_layout_gantt(df, output_path="career_gantt_final.png"):
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    df["duration"] = (df["end"] - df["start"]).dt.days

    category_colors = {
        "교육": "#90be6d",
        "근무": "#577590",
        "자격증": "#f9c74f"
    }

    fig, ax = plt.subplots(figsize=(27, 7))
    bar_y = 0.6
    bar_height = 0.35
    arrow_height = 0.15
    day_event_offsets = {}  # key: rounded date → layer index
    layer_gap = 0.15        # 계단 간격 (줄임)
    max_layer = 10          # 최대 몇 층까지 허용할지

    # 배경 회색 바 (하단 타임라인)
    buffer_days = 90
    timeline_start = df["start"].min() - pd.Timedelta(days=buffer_days)
    timeline_end = df["end"].max() + pd.Timedelta(days=buffer_days)

    ax.add_patch(patches.Rectangle(
        (mdates.date2num(timeline_start), 0),
        (timeline_end - timeline_start).days,
        0.15,
        facecolor="#333333",
        zorder=0
    ))

    # 하단 월 텍스트
    current = timeline_start.replace(month=1, day=1)
    while current <= timeline_end:
        ax.text(current, 0.075, current.strftime('%Y'), ha='center', va='center', color='white', fontsize=8)
        current += pd.DateOffset(years=1)

    # 기간이 있는 항목들의 레이어를 계산하기 위한 함수
    def calculate_layer_for_duration_items(df):
        duration_items = df[df["duration"] > 1].copy()
        if len(duration_items) == 0:
            return {}

        # 시작 시간순으로 정렬하고 원본 인덱스 보존
        duration_items = duration_items.sort_values('start')
        layers = {}  # index -> layer
        occupied_layers = []  # [(start, end, layer), ...]

        for original_idx, row in duration_items.iterrows():
            start_date = row['start']
            end_date = row['end']

            # 현재 항목과 겹치는 레이어들 찾기
            current_layer = 0
            while True:
                # 현재 레이어에서 겹치는 항목이 있는지 확인
                overlap = False
                for occ_start, occ_end, occ_layer in occupied_layers:
                    if occ_layer == current_layer:
                        # 겹치는지 확인 (시작일이 다른 항목 종료일 이전이고, 종료일이 다른 항목 시작일 이후)
                        if start_date < occ_end and end_date > occ_start:
                            overlap = True
                            break

                if not overlap:
                    break
                current_layer += 1

            layers[original_idx] = current_layer
            occupied_layers.append((start_date, end_date, current_layer))

        return layers

    # 기간 항목들의 레이어 계산
    duration_layers = calculate_layer_for_duration_items(df)

    for row in df.itertuples():
        color = category_colors.get(row.category, "#cccccc")
        if hasattr(row, 'label') and '\\n' in str(row.label):
            label = str(row.label).replace('\\n', '\n')  # JSON 문자열에서 \n 처리
        else:
            label = "\n".join(textwrap.wrap(str(row.label), width=10))

        # ▼ 아이템 표시 (duration <= 1 인 경우)
        if row.duration <= 1:
            x = mdates.date2num(row.start)
            date_key = row.start.date()

            current_layer = day_event_offsets.get(date_key, 0)
            while current_layer in day_event_offsets.values():
                current_layer += 1
            day_event_offsets[date_key] = current_layer
            layer_y = 1.3 + current_layer * layer_gap  # 년도 위 계단식 y 위치 (더 높게)

            # ▼ 표시
            ax.text(x, 0.15 + 0.04, '▼', ha='center', va='center', fontsize=14, color=color)

            # 선 연결 (▼ 아래 → 위로)
            ax.plot([x, x], [0.15 + 0.04 - 0.02, layer_y - 0.05], linestyle=":", color=color, linewidth=1)

            # 날짜와 라벨을 위아래로 가깝게 배치
            date_label = f"({row.start.strftime('%Y.%m.%d')})"
            label_text = str(row.label).replace('\\n', '\n') if hasattr(row, 'label') and '\\n' in str(row.label) else str(row.label)

            # 날짜를 아래쪽에, 라벨을 바로 위쪽에 배치
            ax.text(x, layer_y, date_label, ha='center', va='bottom', fontsize=6)
            ax.text(x, layer_y + 0.12, label_text, ha='center', va='bottom', fontsize=7)

        else:
            start_num = mdates.date2num(row.start)
            width = row.duration

            # 레이어에 따른 y 위치 계산
            item_layer = duration_layers.get(row.Index, 0)
            current_bar_y = bar_y + item_layer * (bar_height + 0.1)  # 겹치면 위로 배치

            # 기간 박스
            box = patches.FancyBboxPatch(
                (start_num, current_bar_y - bar_height / 2),
                width, bar_height,
                boxstyle="round,pad=0.02",
                facecolor=color,
                edgecolor='none'  # 테두리 제거
            )
            ax.add_patch(box)

            # 라벨 중앙에 출력 (줄바꿈 포함)
            center_x = mdates.date2num(row.start + pd.Timedelta(days=row.duration / 2))
            ax.text(center_x, current_bar_y, label, ha='center', va='center', fontsize=8, color='black')

            # 시작~종료 텍스트 (YYYY.MM–YYYY.MM)
            start_str = row.start.strftime('%Y.%m')
            end_str = row.end.strftime('%Y.%m')
            date_label = f'({start_str}–{end_str})'
            ax.text(center_x, current_bar_y + 0.25, date_label, ha='center', va='bottom', fontsize=6, color='black')

    # 시작/종료 라벨 하단
    ax.text(timeline_start, -0.1, f"{timeline_start.strftime('%m.%d.%Y')}\nProject Start",
            fontsize=8, ha='left', va='top', color='blue')
    ax.text(timeline_end, -0.1, f"{timeline_end.strftime('%m.%d.%Y')}\nProject End",
            fontsize=8, ha='right', va='top', color='blue')

    # 축 정리
    ax.set_ylim(-0.6, 2.4)
    ax.set_xlim(timeline_start, timeline_end)
    ax.axis('off')
    ax.set_title("Career Timeline", fontsize=16, weight='bold', pad=20)

    # 범례 추가
    legend_elements = [patches.Patch(facecolor=color, label=category)
                      for category, color in category_colors.items()
                      if category in df['category'].values]
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))

    plt.tight_layout()

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 경고 숨기고 저장
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        plt.savefig(output_path, dpi=200, bbox_inches='tight',
                   facecolor='white', edgecolor='none')

    plt.close()
    print(f"✅ 간트 차트 저장 완료 → {output_path}")
    return output_path

# 메인 함수
def main():
    input_json = "timeline.json"
    output_img = "output/career_gantt_final.png"

    if not os.path.exists(input_json):
        print("❌ timeline.json 파일이 존재하지 않습니다.")
        return

    try:
        df = load_json(input_json)
        print(f"📊 {len(df)}개의 타임라인 항목을 처리합니다.")
        generate_final_layout_gantt(df, output_path=output_img)
        print("🎉 타임라인 생성이 완료되었습니다!")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise

if __name__ == "__main__":
    main()