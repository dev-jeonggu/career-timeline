from utils.file_utils import load_json, clean_output_dir
from plot.gantt_generator import generate_final_layout_gantt
import os

def main():
    input_json = "data/timeline.json"
    output_img = "output/career_gantt_final.png"

    if not os.path.exists(input_json):
        print("❌ timeline.json 파일이 존재하지 않습니다.")
        return

    clean_output_dir("output")
    df = load_json(input_json)
    print(f"📊 {len(df)}개의 타임라인 항목을 처리합니다.")

    result_path = generate_final_layout_gantt(df, output_img)

    if os.path.exists(result_path):
        print(f"🎉 타임라인 생성 완료! 파일 크기: {os.path.getsize(result_path):,} bytes")
        print(f"📁 파일 위치: {os.path.abspath(result_path)}")
    else:
        print("❌ 파일 생성 실패!")

if __name__ == "__main__":
    main()