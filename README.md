# Career Timeline
개발자의 커리어를 시각적으로 표현하는 간트 차트 스타일의 타임라인 생성기입니다.  
JSON 형식으로 경력을 입력하면, 연도별로 정리된 이미지 형태의 경력 타임라인을 자동으로 생성합니다.

## 👩🏻‍💻 Developer
| jeonggu.kim<br />(김정현) |
|:---:|
| <a href="https://github.com/dev-jeonggu"> <img src="https://avatars.githubusercontent.com/dev-jeonggu" width=100px alt="_"/> </a> |
| <a href="https://github.com/dev-jeonggu">@dev-jeonggu</a> |

## 🛠️ Stack
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=Python&logoColor=white)  

## ✨ Main Feature
    - 경력 데이터를 기반으로 타임라인 그래프 시각화
    - 연도별 배치, 기간 자동 계산, 색상 커스터마이징 지원
    - 이미지 형태(`.png`)로 저장 가능하여 포트폴리오나 이력서에 활용 가능
    - 커리어 중복/공백 구간 없이 자연스럽게 정렬
    - 경력 시작 연도와 끝 연도 기준 자동 정렬

## 📁 File Structure
    career-timeline/
    ├── data/
    │   └── career_data.json        # 커리어 데이터 입력 파일
    ├── output/
    │   └── career_gantt_final.png  # 생성된 타임라인 이미지
    ├── plot/  
    │   └── gantt_generator.py      # 간트 차트 형태의 타임라인 이미지를 생성 스크립트
    ├── utils/  
    │   └── file_util.py            # 데이터 처리 및 폴더 정리에 사용되는 유틸리티 함수 스크립트
    │   └── font_config.py          # 한국어 폰트 설정 스크립트
    ├── main.py                     # 메인 실행 스크립트
    └── README.md                   # 프로젝트 설명 문서

## 📊 data sample
    [
    {
      "label": "한국성서대학교 컴퓨터소프트웨어학과 졸업",
      "start": "2017-03-01",
      "end": "2021-02-16",
      "category": "교육"
    },
      ...
    ]

## 🚀 Usage example
    1. `career_data.json`에 경력 데이터를 입력합니다.
    2. Python 스크립트를 실행하면 `output/` 폴더에 이미지 파일이 생성됩니다.
    3. 생성된 이미지를 README, 이력서, 포트폴리오 등에 자유롭게 활용하세요.

## 📸 sample image
    `output/sample.png` 참고
