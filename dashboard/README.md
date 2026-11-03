# 홈런 · 최소 실험 비교 대시보드

Google Sheets에 저장된 EXP01 · EXP06의 전체 점수와 Q01 답변 비교.
GPU · Colab · LLM API 불필요. Google Sheets 읽기 전용. 원본 셀 변경 없음.

## 파일

```text
dashboard/
├── app.py                           # 데이터 읽기 · 비교 화면
├── requirements.txt                 # 설치할 패키지
├── README.md                        # 연결 · 실행 · 배포 방법
├── .gitignore                       # 실제 인증 정보 업로드 제외
└── .streamlit/
    └── secrets.toml.example          # 인증 정보 형식 예시
```

화면 순서: 실험 선택 → 총점 · 치명적 오류 → 모델 · 프롬프트 설정 → Q01 답변 · 사람 검토.
질문 3개의 점수로 전체 총점 계산. Q01만 상세 답변 표시.
현재는 rubric-v2 · EXP01 · EXP06, 각 질문 Q01 · Q04 · Q05 1행씩 지원.
평가 버전이나 질문 구성이 바뀌면 코드의 평가 설정을 먼저 업데이트.
다른 실험 · 질문 선택 · 항목별 채점 · 기술별 상세 설정은 후속 작업.

## 1. Google Sheets 연결 설정

Streamlit 가입과 별도로 Google Sheets 인증 설정이 한 번 필요.

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성 또는 선택.
2. `API 및 서비스`에서 **Google Sheets API** 검색 후 활성화.
3. `IAM 및 관리자 → 서비스 계정`에서 서비스 계정 생성. 이 앱만을 위해 프로젝트 전체 역할을 추가할 필요 없음.
4. 해당 서비스 계정의 `키 → 키 추가 → 새 키 만들기 → JSON`으로 키 파일 다운로드.
5. JSON의 `client_email` 값을 확인. 팀원이 아니라 앱이 사용할 별도 계정 이메일.
6. [기존 스프레드시트](https://docs.google.com/spreadsheets/d/1kvg4lgNtJ3nUugUMXFkYg0HxwuqgqrXR-Nw-KYrvN34/edit)의 공유에서 이 이메일을 **뷰어**로 추가. 전체 공개로 바꿀 필요 없음.
7. `.streamlit/secrets.toml.example`의 각 예시 값을 JSON의 같은 이름 값으로 교체하여 앱 Secrets에 입력.

코드는 `open_by_key`와 Sheets API 읽기 전용 범위만 사용. Drive API 검색 · 파일 생성 · 시트 쓰기를 사용하지 않음.

### Secrets 입력 시 주의할 한 가지

`private_key`는 줄바꿈을 `\n`으로 유지한 큰따옴표 문자열로 입력.
예시 파일은 형식만 보여주며 실제 인증 정보는 들어 있지 않음.
실제 `secrets.toml` · 서비스 계정 JSON은 GitHub나 채팅에 올리지 않음.

## 2. GitHub → Streamlit Cloud 배포

기존 저장소 `jud3-hub/first-rental-guide` 사용 가능. 다음 작업은 사용자가 진행.

1. GitHub 저장소에서 `Add file → Upload files` 선택.
2. 저장소 루트에 `dashboard` 폴더를 올리되 `app.py`, `requirements.txt`, `README.md`를 포함. 인증 예시 파일은 참고용이며 배포 필수 파일이 아님.
3. 로컬 Git을 사용한다면 숨김 파일 `.gitignore`도 함께 추가.
4. Streamlit Community Cloud에서 `Create app` 또는 `New app` 선택.
5. 저장소와 실제 기본 브랜치 선택. 메인 파일 경로는 `dashboard/app.py`.
6. 배포 설정의 `Advanced settings → Secrets`에 실제 값으로 바꾼 TOML 입력. Python은 3.12 권장.
7. 배포 실행. 배포 후 입력할 경우 앱 설정의 Secrets 저장 후 다시 실행.

서비스 계정 생성 · 시트 권한 공유 · Streamlit 외부 배포는 별도 설정 필요.
대시보드를 공개하면 앱 방문자는 화면에 표시된 답변 · 검토 의견을 볼 수 있음.

## 3. 로컬 실행 (선택)

명령은 `dashboard` 폴더에서 실행.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

`secrets.toml`에 실제 값을 입력한 뒤 실행:

```bash
streamlit run app.py
```

Colab에서 Streamlit 서버를 띄우거나 우회 터널을 추가할 필요 없음.
직접 의존성 버전은 로컬 검증에 사용한 버전으로 고정.

## 확인한 동작

- 기존 결과를 사용한 데이터 변환: EXP01 합계 1점 · EXP06 합계 9점 확인.
- Streamlit AppTest: 첫 화면 · 기준/비교 실험 반전 · 인증 누락 안내 확인.
- 중복 행 · 질문 누락 · 다른 실행 혼합 · 잘못된 점수는 오류로 처리.
- 빈 점수는 미채점, 사람 판정이 빈칸이면 검토 미완료로 유지.
- 실제 Google Sheets 서비스 계정 인증과 외부 배포는 아직 미검증. 사용자 인증 설정 이후 확인 필요.

## 읽는 데이터

|탭|용도|현재 읽기 범위|
|---|---|---|
|결과 데이터|답변 · 점수 · 모델 · 검토 기록|A1:T200|
|실험 비교|실험 이름 · 합계 일치 검증|A1:N65|
|평가 기준|Q01 원문 · 기준 답변 · 근거|A1:E24|

열 이름으로 표를 찾아 읽으므로 상단 제목 · 빈 줄을 데이터로 취급하지 않음.
원본이 읽기 범위를 넘어 커지면 이 세 범위를 늘릴 것.
새로고침 버튼은 읽기 캐시를 비우고 다시 조회. 자동 캐시 만료는 60초이며 이후 페이지 상호작용/재실행 시 최신 값 조회.
고정 타이머로 자동 조회하는 기능은 없음.

## 해석 규칙

- 빈 점수는 미채점. 빈 오류 판정은 미판정.
- 실험별로 3개 질문이 다 채점돼야 전체 점수 표시.
- 같은 실행 · 질문 · 루브릭 중복 또는 다른 실행 혼합은 오류 안내.
- 사람 검토는 치명적 오류 판정의 검토이며, AI 점수의 사람 재채점을 의미하지 않음.
- 기존 요약 탭의 EXP01 기준 차이를 그대로 쓰지 않고 선택한 기준에 맞춰 차이 계산.
- 모델 · 프롬프트 버전은 원본 기록대로 표시. 법령 원문 직접 제공를 RAG로 표시하지 않음.
- 질문 3개 · 각 1회 실행 결과를 전체 모델 성능으로 일반화하지 않음.

## 연결 오류 확인 순서

1. Secrets에 `[gcp_service_account]` 블록이 있는지 확인.
2. 실제 JSON에서 값을 복사했는지 확인.
3. 같은 JSON의 서비스 계정 이메일을 시트에 뷰어로 공유했는지 확인.
4. 같은 Google Cloud 프로젝트에서 Sheets API를 활성화했는지 확인.
5. 탭 이름의 띄어쓰기 `실험 비교` · `결과 데이터` · `평가 기준` 유지 여부 확인.

## 공식 문서

- [Streamlit 비공개 Sheets 연결 개요](https://docs.streamlit.io/develop/tutorials/databases/private-gsheet)
- [gspread 서비스 계정 인증](https://docs.gspread.org/en/latest/oauth2.html)
- [Streamlit Community Cloud 배포](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app)

이 코드는 Streamlit 화면과 gspread 읽기 연결을 사용. 위 Streamlit 예제의 GSheetsConnection 대신 gspread를 직접 사용하여 API 권한을 읽기 전용으로 제한.
