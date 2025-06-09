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
import shutil
import time

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
        "자격증": "#f9c74f",
        "수상": "#ffcce5"
    }

    fig, ax = plt.subplots(figsize=(32, 10))
    bar_y = 0.8
    bar_height = 0.35
    arrow_height = 0.15
    day_event_offsets = {}  # key: rounded date → layer index
    layer_gap = 0.25

    # 배경 회색 바 (하단 타임라인)
    timeline_start = df["start"].min()
    timeline_end = df["end"].max()

    # 여백을 좀 더 늘려서 2017년이 안 짤리게
    buffer_start_days = 45  # 15 → 45일로 증가
    buffer_end_days = 365  # 오른쪽 여백을 1년으로 늘림
    timeline_start = timeline_start - pd.Timedelta(days=buffer_start_days)
    timeline_end = timeline_end + pd.Timedelta(days=buffer_end_days)

    print(f"🕐 시간 범위: {timeline_start.strftime('%Y-%m-%d')} ~ {timeline_end.strftime('%Y-%m-%d')}")

    ax.add_patch(patches.Rectangle(
        (mdates.date2num(timeline_start), 0),
        (timeline_end - timeline_start).days,
        0.15,
        facecolor="#333333",
        zorder=0
    ))

    # 하단 년도 텍스트 - 데이터 범위에 맞게 조정
    start_year = df["start"].min().year
    end_year = df["end"].max().year + 1

    for year in range(start_year, end_year + 1):
        year_date = datetime(year, 1, 1)
        # 시간 범위 내에 있는 년도만 표시
        if timeline_start <= year_date <= timeline_end:
            ax.text(year_date, 0.075, str(year), ha='center', va='center', color='white', fontsize=14)
        else:
            # 범위를 벗어나도 데이터에 해당하는 년도면 표시 (예: 2017년 첫 데이터)
            year_data_in_df = df[df["start"].dt.year == year]["start"].min()
            if pd.notna(year_data_in_df) and timeline_start <= year_data_in_df <= timeline_end:
                ax.text(year_data_in_df, 0.075, str(year), ha='center', va='center', color='white', fontsize=14)

    # 기간이 있는 항목들의 레이어를 계산하기 위한 함수
    def calculate_layer_for_duration_items(df):
        duration_items = df[df["duration"] > 1].copy()
        if len(duration_items) == 0:
            return {}

        # 시작 시간순으로 정렬하고 원본 인덱스 보존
        duration_items = duration_items.sort_values('start')
        layers = {}  # index -> layer
        occupied_layers = []  # [(start, end, layer), ...]

        # 최대 레이어 제한 설정
        MAX_LAYERS = 5  # 최대 5단계까지 올라가도록 늘림

        for original_idx, row in duration_items.iterrows():
            start_date = row['start']
            end_date = row['end']

            # 현재 항목과 겹치는 레이어들 찾기
            current_layer = 0
            while current_layer < MAX_LAYERS:  # 최대 레이어 제한
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

            # 최대 레이어에 도달하면 그냥 그 레이어에 배치
            if current_layer >= MAX_LAYERS:
                current_layer = MAX_LAYERS - 1

            layers[original_idx] = current_layer
            occupied_layers.append((start_date, end_date, current_layer))

        return layers

    # 기간 항목들의 레이어 계산
    duration_layers = calculate_layer_for_duration_items(df)

    for row in df.itertuples():
        color = category_colors.get(row.category, "#cccccc")

        # 라벨 처리 개선
        if hasattr(row, 'label'):
            raw_label = str(row.label)
            print(f"🏷️ 처리 중인 라벨: '{raw_label}'")  # 디버깅

            # \\n을 실제 줄바꿈으로 변환
            if '\\n' in raw_label:
                label = raw_label.replace('\\n', '\n')
                print(f"   → 변환 후: '{label}'")
            else:
                # 자동 줄바꿈 (긴 텍스트용)
                label = "\n".join(textwrap.wrap(raw_label, width=15))
        else:
            label = "라벨 없음"

        # ▼ 아이템 표시 (duration <= 1 인 경우)
        if row.duration <= 1:
            x = mdates.date2num(row.start)
            date_key = row.start.date()

            current_layer = day_event_offsets.get(date_key, 0)
            while current_layer in day_event_offsets.values():
                current_layer += 1
            day_event_offsets[date_key] = current_layer

            # 일일 이벤트도 최대 높이 제한
            MAX_DAY_LAYERS = 4  # 더 많은 레이어 허용
            if current_layer >= MAX_DAY_LAYERS:
                current_layer = current_layer % MAX_DAY_LAYERS

            layer_y = 1.5 + current_layer * layer_gap  # 시작 위치를 더 올림

            # ▼ 표시
            ax.text(x, 0.15 + 0.04, '▼', ha='center', va='center', fontsize=20, color=color)

            # 선 연결 (▼ 아래 → 위로)
            ax.plot([x, x], [0.15 + 0.04 - 0.02, layer_y - 0.05], linestyle=":", color=color, linewidth=2)

            # 날짜와 라벨을 위아래로 가깝게 배치
            date_label = f"({row.start.strftime('%Y.%m.%d')})"
            label_text = label

            # 날짜를 아래쪽에, 라벨을 바로 위쪽에 배치
            ax.text(x, layer_y, date_label, ha='center', va='bottom', fontsize=10)
            ax.text(x, layer_y + 0.08, label_text, ha='center', va='bottom', fontsize=16)

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
            ax.text(center_x, current_bar_y, label, ha='center', va='center', fontsize=16, color='black', weight='bold')

            # 시작~종료 텍스트 (YYYY.MM–YYYY.MM)
            start_str = row.start.strftime('%Y.%m')
            end_str = row.end.strftime('%Y.%m')
            date_label = f'({start_str}–{end_str})'
            ax.text(center_x, current_bar_y + 0.2, date_label, ha='center', va='bottom', fontsize=10, color='black')

    # 축 설정 - 정확한 범위로 설정
    start_date_num = mdates.date2num(timeline_start)
    end_date_num = mdates.date2num(timeline_end)

    ax.set_xlim(start_date_num, end_date_num)
    ax.set_ylim(-0.1, 4.0)  # y축 범위를 크게 늘림
    ax.axis('off')

    print(f"📐 X축 범위: {start_date_num} ~ {end_date_num}")

    # 범례 추가
    legend_elements = [patches.Patch(facecolor=color, label=category)
                      for category, color in category_colors.items()
                      if category in df['category'].values]
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.99, 0.95), fontsize=16)

    # 여백 제거 - 더 공격적으로
    fig.subplots_adjust(left=0, right=1, top=0.95, bottom=0)  # bottom을 0으로

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 저장 - 완전 여백 제거
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # bbox_inches 없이 저장 (matplotlib의 자동 여백 방지)
        plt.savefig(output_path, dpi=600, facecolor='white', edgecolor='none',
                   format='png', pil_kwargs={'optimize': True})

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

    # 기존 output 폴더와 파일 완전 삭제
    if os.path.exists("output"):
        print("🧹 기존 output 폴더 삭제 중...")
        shutil.rmtree("output")
        print("✅ 기존 파일 삭제 완료")

    # 잠시 대기 (파일 시스템 동기화)
    time.sleep(0.5)

    try:
        df = load_json(input_json)
        print(f"📊 {len(df)}개의 타임라인 항목을 처리합니다.")
        result_path = generate_final_layout_gantt(df, output_path=output_img)

        # 파일 생성 확인
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"🎉 타임라인 생성 완료! 파일 크기: {file_size:,} bytes")
            print(f"📁 파일 위치: {os.path.abspath(result_path)}")
        else:
            print("❌ 파일 생성 실패!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise

if __name__ == "__main__":
    main()