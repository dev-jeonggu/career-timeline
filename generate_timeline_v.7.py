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

# 텍스트 높이 계산 함수 (대략적인 값)
# 이 함수는 실제 렌더링 전의 텍스트 높이를 정확히 예측하기 어렵습니다.
# 경험적인 값을 사용하여 폰트 크기, 줄 수에 따른 상대적인 높이를 추정합니다.
# 필요에 따라 line_height_per_font_size 값을 조정하여 정확도를 높일 수 있습니다.
def get_text_height_estimate(text, fontsize):
    # 이 값은 폰트 크기 1당 Y축 데이터 좌표계에서 차지하는 대략적인 높이입니다.
    # 폰트, DPI, 그림 크기 등에 따라 달라질 수 있으므로 조정이 필요할 수 있습니다.
    line_height_per_font_size = 0.0055
    num_lines = len(text.split('\n'))

    # 텍스트의 Y축 높이 (데이터 좌표계)
    estimated_height = (fontsize * line_height_per_font_size * num_lines)
    return estimated_height

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

    fig, ax = plt.subplots(figsize=(32, 10))  # 더 큰 사이즈로 변경

    # 텍스트 및 바의 기본 높이 설정
    base_bar_height = 0.35 # 기간 박스 기본 높이
    text_padding_y = 0.08 # 텍스트 위아래 패딩

    # 일일 이벤트의 Y 좌표 관리 (겹침 방지)
    # key: date (datetime.date)
    # value: list of (event_bottom_y, event_top_y) - 이미 사용된 Y 범위
    day_event_occupied_y = {}
    day_event_start_y = 1.0 # 일일 이벤트가 시작될 가장 낮은 Y 좌표 (하단 타임라인과 기간 이벤트 사이)

    # 배경 회색 바 (하단 타임라인)
    timeline_start = df["start"].min()
    timeline_end = df["end"].max()

    # 여백을 좀 더 늘려서 2017년이 안 짤리게, 오른쪽도 2026년까지 보이게
    buffer_start_days = 45
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

    # 하단 년도 텍스트 - 2026년까지 표시
    start_year = df["start"].min().year
    end_year = max(df["end"].max().year, 2026)  # 최소 2026년까지 표시

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

    # 기간이 있는 항목들의 레이어를 계산하기 위한 함수 (계단식 배치)
    def calculate_layer_for_duration_items(df):
        duration_items = df[df["duration"] > 1].copy()
        if len(duration_items) == 0:
            return {}

        # 시작 시간순으로 정렬하고 원본 인덱스 보존
        duration_items = duration_items.sort_values('start')
        layers = {}  # index -> layer
        # 각 레이어의 마지막 항목이 끝나는 날짜 (mdates.date2num)
        # key: layer number, value: end_date_num
        layer_end_dates = {}

        MAX_LAYERS = 10 # 최대 허용 레이어 수

        for original_idx, row in duration_items.iterrows():
            start_date_num = mdates.date2num(row['start'])
            end_date_num = mdates.date2num(row['end'])

            # 이 항목을 배치할 레이어 찾기
            found_layer = False
            for current_layer in range(MAX_LAYERS):
                # 해당 레이어의 마지막 항목이 끝나는 날짜와 현재 항목의 시작 날짜 비교
                if current_layer not in layer_end_dates or start_date_num >= layer_end_dates[current_layer]:
                    layers[original_idx] = current_layer
                    layer_end_dates[current_layer] = end_date_num # 이 레이어의 마지막 항목 종료일 업데이트
                    found_layer = True
                    break

            # 모든 레이어가 꽉 찼으면 (겹치면) 다음 레이어에 강제로 배치
            if not found_layer:
                # MAX_LAYERS를 넘어서는 레이어에 배치 (시각적으로는 MAX_LAYERS-1 에 겹칠 수 있음)
                # 이 경우는 매우 드물거나, MAX_LAYERS를 더 늘려야 함
                current_layer = max(layer_end_dates.keys()) + 1 if layer_end_dates else 0
                layers[original_idx] = current_layer
                layer_end_dates[current_layer] = end_date_num
                print(f"⚠️ 경고: MAX_LAYERS({MAX_LAYERS}) 초과. 새로운 레이어 {current_layer}에 배치.")

        return layers

    # 기간 항목들의 레이어 계산
    duration_layers = calculate_layer_for_duration_items(df)

    # 각 레이어의 가장 높은 Y 좌표를 추적하여 동적 Y축 계산에 활용
    # key: layer number, value: max_height_in_layer (해당 레이어에서 가장 높았던 박스 or 텍스트 높이)
    max_height_per_duration_layer = {}

    # 모든 아이템을 그립니다.
    for row in df.itertuples():
        color = category_colors.get(row.category, "#cccccc")

        # 라벨 처리 (줄바꿈 및 자동 줄바꿈)
        raw_label = str(row.label)
        if '\\n' in raw_label:
            label = raw_label.replace('\\n', '\n')
        else:
            label = "\n".join(textwrap.wrap(raw_label, width=15))

        # 텍스트의 예상 높이 계산
        estimated_label_height = get_text_height_estimate(label, 16)


        # ▼ 아이템 표시 (duration <= 1 인 경우: 하루 기한 데이터)
        if row.duration <= 1:
            x = mdates.date2num(row.start)
            date_key = row.start.date()

            # 해당 날짜에 이미 사용된 Y축 범위 리스트 가져오기
            occupied_y_ranges_today = day_event_occupied_y.get(date_key, [])

            # 새로운 이벤트의 Y 위치 찾기
            # date_label의 높이도 고려
            estimated_date_label_height = get_text_height_estimate(f"({row.start.strftime('%Y.%m.%d')})", 10)

            # 이벤트 전체가 차지할 예상 높이 (라벨 + 날짜 + 여백 + 선)
            current_event_full_height = estimated_label_height + estimated_date_label_height + 0.1 # 날짜와 라벨 사이 여백 및 선 길이

            # 현재 이벤트를 배치할 가장 낮은 Y축 시작점
            current_event_y_bottom = day_event_start_y # 기본 시작 위치

            # 겹치지 않는 Y 위치를 찾을 때까지 반복
            found_position = False
            while not found_position:
                overlap_found = False
                event_top_y = current_event_y_bottom + current_event_full_height
                for occ_bottom, occ_top in occupied_y_ranges_today:
                    # 현재 이벤트와 기존 이벤트가 Y축으로 겹치는지 확인
                    if not (current_event_y_bottom >= occ_top or event_top_y <= occ_bottom):
                        overlap_found = True
                        current_event_y_bottom = occ_top + 0.05 # 겹치면 다음 사용 가능한 위치로 이동 (약간의 간격)
                        break
                if not overlap_found:
                    found_position = True

            # 새로운 Y 범위 추가
            day_event_occupied_y.setdefault(date_key, []).append((current_event_y_bottom, current_event_y_bottom + current_event_full_height))
            day_event_occupied_y[date_key].sort() # 정렬하여 다음 탐색 효율 높임

            # 날짜와 라벨 배치
            date_label = f"({row.start.strftime('%Y.%m.%d')})"
            ax.text(x, current_event_y_bottom, date_label, ha='center', va='bottom', fontsize=10)
            ax.text(x, current_event_y_bottom + estimated_date_label_height + 0.05, label, ha='center', va='bottom', fontsize=16)

            # ▼ 표시
            arrow_y = 0.15 + 0.04
            ax.text(x, arrow_y, '▼', ha='center', va='center', fontsize=20, color=color)

            # 선 연결 (▼ 아래 → 위로)
            ax.plot([x, x], [arrow_y - 0.02, current_event_y_bottom - 0.05], linestyle=":", color=color, linewidth=2)


        else: # duration > 1 인 경우 (기간이 있는 항목)
            start_num = mdates.date2num(row.start)
            width = row.duration

            # 레이어에 따른 y 위치 계산
            item_layer = duration_layers.get(row.Index, 0)

            # 텍스트 높이에 따라 bar_height 동적 조정
            # 텍스트 높이 + 위아래 패딩 + 기본 바 높이의 최소값 보장
            current_bar_height = max(base_bar_height, estimated_label_height + text_padding_y * 2)

            # 각 레이어의 실제 시작 Y 위치를 계산 (겹치지 않게 쌓아 올림)
            current_bar_y_bottom_for_layer = 0.5 # 기간 이벤트 시작 Y 좌표
            for l in range(item_layer):
                # 이전 레이어에서 가장 높았던 박스 or 텍스트 높이를 고려하여 다음 레이어 시작 위치 결정
                current_bar_y_bottom_for_layer += max_height_per_duration_layer.get(l, base_bar_height + 0.2) + 0.1

            current_bar_y = current_bar_y_bottom_for_layer + current_bar_height / 2 # 박스의 중앙 Y 좌표

            # 기간 박스
            box = patches.FancyBboxPatch(
                (start_num, current_bar_y - current_bar_height / 2),
                width, current_bar_height,
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
            # 텍스트 높이를 고려하여 박스 위쪽에 배치
            ax.text(center_x, current_bar_y + current_bar_height / 2 + 0.05, date_label, ha='center', va='bottom', fontsize=10, color='black')

            # 해당 레이어의 최대 높이 업데이트 (다음 레이어 계산에 사용)
            # 여기서는 현재 박스의 높이(current_bar_height)를 저장
            max_height_per_duration_layer[item_layer] = max(max_height_per_duration_layer.get(item_layer, 0), current_bar_height)


    # 축 설정 - 정확한 범위로 설정
    start_date_num = mdates.date2num(timeline_start)
    end_date_num = mdates.date2num(timeline_end)

    ax.set_xlim(start_date_num, end_date_num)

    # Y축 범위 동적 조절
    max_y_all_events = 0

    # 1. 일일 이벤트의 최대 Y 좌표
    for date_key in day_event_occupied_y:
        for _, top_y in day_event_occupied_y[date_key]:
            max_y_all_events = max(max_y_all_events, top_y)

    # 2. 기간 이벤트의 최대 Y 좌표
    # 각 레이어의 실제 최종 Y 좌표를 합산하여 계산
    current_duration_y_offset = 0.5 # 기간 이벤트 시작 Y 좌표
    for l in sorted(max_height_per_duration_layer.keys()):
        # 이전 레이어의 높이 + 간격만큼 Y 오프셋을 추가
        current_duration_y_offset += max_height_per_duration_layer.get(l, base_bar_height + 0.2) + 0.1
    max_y_all_events = max(max_y_all_events, current_duration_y_offset)

    ax.set_ylim(-0.1, max(max_y_all_events + 0.5, 5.0)) # 최소 5.0은 유지, 계산된 최대 Y 값에 여유 공간 추가

    ax.axis('off')

    print(f"📐 X축 범위: {start_date_num} ~ {end_date_num}")

    # 범례 추가
    legend_elements = [patches.Patch(facecolor=color, label=category)
                      for category, color in category_colors.items()
                      if category in df['category'].values]
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.99, 0.95), fontsize=16)

    # 여백 제거 - 더 공격적으로
    fig.subplots_adjust(left=0, right=1, top=0.95, bottom=0)

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 저장 - 완전 여백 제거
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
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