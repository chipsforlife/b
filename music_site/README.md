# MoodTune — AI 프롬프트 음악 생성 커뮤니티

프롬프트 한 줄로 AI가 배경음악(BGM)을 만들어주고, 만든 곡을 게시글로 공유·재생하고
댓글로 소통할 수 있는 커뮤니티 웹앱입니다. 기획 배경/컨셉/기능 정의는 저장소 루트의
[`기능정의서.md`](../기능정의서.md)를 참고하세요.

## 기술 스택

- 백엔드: Python + Flask
- 프론트엔드: HTML(Jinja2) + CSS + Vanilla JS
- 로그인/회원가입: Firebase Authentication (이메일/비밀번호, 클라이언트 JS SDK)
- 데이터 저장: Firestore (`firebase-admin`, 서버에서만 접근)
- 음악 생성: Hugging Face Inference Providers — Stable Audio (서버에서 호출, API 키는
  브라우저에 노출되지 않음)
- 오케스트라 악보 생성: OpenAI(ChatGPT) — 무드/템포/프롬프트로 MusicXML 악보 작곡 (서버에서 호출)

## 화면 / 기능

1. 로그인 / 회원가입 (`/login`)
2. 메인 페이지 — 게시글(생성된 곡) 목록 + 검색 (`/`, `?q=`)
3. 게시글 작성 — 프롬프트/장르/길이 + **무드(필수)/템포** 입력 → 음악 + 오케스트라 악보
   동시 생성 → 저장 (`/new`, 로그인 필요)
4. 게시글 상세 — 오디오 재생, 악보(MusicXML) 다운로드/미리보기, 댓글 (`/post/<id>`)
5. 댓글 — 로그인한 사용자만 작성 가능, 조회는 누구나 가능

### 무드 커스터마이징

게시글 작성 화면에서 오케스트라 악보의 분위기를 드롭다운으로 고르고(밝고 경쾌하게, 슬프고
잔잔하게, 웅장하고 영웅적으로, 신비롭게, 평화롭게, 긴장감 있게, 승리에 찬 팡파르처럼, 애수
어린, 장난스럽게, 어둡고 무겁게), 템포(느리게/보통/빠르게)를 버튼으로 선택합니다. 이 값과
프롬프트를 함께 ChatGPT에 전달해 오케스트라 편성의 MusicXML 악보를 만듭니다.

## 지금 바로 실행해보기 (설정 없이, 데모 모드)

Firebase 프로젝트나 Hugging Face/OpenAI 키가 아직 없어도 전체 흐름(로그인 → 음악+악보
생성 → 재생 → 댓글)을 바로 체험할 수 있습니다.

```bash
cd music_site
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

`http://127.0.0.1:5002` 접속 → 아무 이메일/비밀번호로 회원가입하면 바로 로그인됩니다.
이 상태에서는 다음과 같이 동작합니다.

- `GOOGLE_APPLICATION_CREDENTIALS`가 없으면 **DEMO_MODE**로 전환되어, 게시글/댓글이
  Firestore 대신 서버 메모리에 저장됩니다 (서버 재시작 시 초기화).
- 프론트엔드에 `static/js/firebase-config.js`가 없으면 로그인도 브라우저
  localStorage 기반의 임시 계정으로 동작합니다 (실제 Firebase 인증 아님).
- `HF_API_TOKEN`이 없으면 실제 Stable Audio 대신 서버가 로컬에서 짧은 화음
  사운드를 합성해 대신 재생해줍니다("🧪 데모 사운드" 배지로 표시).
- `OPENAI_API_KEY`가 없으면 실제 ChatGPT 작곡 대신 선택한 무드/템포에 맞는 간단한
  멜로디를 로컬에서 만들어 MusicXML로 저장해줍니다(데모 문구로 표시).

화면 상단에는 데모 모드임을 알리는 배너가 표시됩니다. 아래 "준비물" 절차대로 실제
Firebase 프로젝트와 API 키들을 연결하면, 코드 변경 없이 자동으로 실제 모드로 전환됩니다.

## 준비물

1. **Firebase 프로젝트**
   - [Firebase Console](https://console.firebase.google.com/)에서 프로젝트 생성
   - **Authentication → 로그인 방법**에서 "이메일/비밀번호" 활성화
   - **Firestore Database** 생성 (테스트 모드 또는 원하는 보안 규칙으로)
   - **프로젝트 설정 → 서비스 계정**에서 비공개 키(JSON) 생성 → 저장소에 커밋하지 말 것
   - **프로젝트 설정 → 일반 → 내 앱**에서 웹 앱을 추가하고 SDK 설정 값(config) 확인

2. **Hugging Face API 키** (Stable Audio 3, Inference Providers)
   - 아직 발급 전이라면 `.env`의 `HF_API_TOKEN`을 비워두면 됩니다. 이 경우 음악 생성 요청은
     로컬 placeholder 사운드로 대체됩니다(위 데모 모드 참고).
   - 발급 후에는 `.env`의 `HF_API_TOKEN`에 키를 넣고, 실제로 사용할 모델 ID를
     `HF_MODEL_ID`에 지정하세요 (기본값은 `stabilityai/stable-audio-open-1.0`).

3. **OpenAI API 키** (ChatGPT — 오케스트라 악보/MusicXML 작곡)
   - [OpenAI API keys](https://platform.openai.com/api-keys)에서 키를 발급받아
     `.env`의 `OPENAI_API_KEY`에 넣습니다. `OPENAI_MODEL`로 모델을 바꿀 수 있습니다
     (기본값 `gpt-4o-mini`).
   - 없어도 로컬 placeholder 멜로디로 대체되어 전체 흐름은 계속 동작합니다.

## 실행 방법

1. **가상환경 생성 및 패키지 설치** (반드시 venv 사용)

   ```bash
   cd music_site
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **백엔드 환경변수 설정**

   ```bash
   cp .env.example .env
   ```

   `.env`를 열어 아래 값을 채웁니다.
   - `GOOGLE_APPLICATION_CREDENTIALS`: 다운로드한 서비스 계정 JSON 파일의 전체 경로
   - `HF_API_TOKEN`, `HF_MODEL_ID`: Hugging Face 관련 값 (키는 추후 발급 예정)
   - `OPENAI_API_KEY`, `OPENAI_MODEL`: OpenAI(ChatGPT) 관련 값
   - `FLASK_SECRET_KEY`: 임의의 문자열

3. **프론트엔드 Firebase 설정**

   ```bash
   cp static/js/firebase-config.example.js static/js/firebase-config.js
   ```

   `firebase-config.js`를 열어 Firebase 웹 앱의 config 값(apiKey, authDomain 등)을 채웁니다.
   이 파일은 `.gitignore`에 등록되어 있어 커밋되지 않습니다.

4. **서버 실행**

   ```bash
   python app.py
   ```

   `http://127.0.0.1:5002` 에서 접속합니다. (포트 5002 — 저장소의 다른 데모 앱들과 동시에
   실행할 수 있도록 다른 포트를 사용합니다.)

## 동작 방식 요약

- 로그인/회원가입은 브라우저에서 Firebase Auth JS SDK로 직접 처리합니다.
- 로그인 후에는 Firebase가 발급한 ID 토큰을 `Authorization: Bearer <token>` 헤더로
  API 요청에 실어 보냅니다.
- 백엔드는 `firebase-admin`으로 토큰을 검증해 사용자를 식별하고, Firestore에 접근합니다
  (클라이언트는 Firestore에 직접 접근하지 않습니다).
- `POST /api/posts` 호출 시 서버가 Hugging Face Inference Providers로 프롬프트를 전달해
  오디오를 생성하고, OpenAI(ChatGPT)에는 프롬프트+무드+템포를 전달해 오케스트라 악보
  (MusicXML)를 작곡시킵니다. 두 결과 파일 모두 `static/generated/`에 저장한 뒤 Firestore에
  게시글로 기록합니다.
- 게시글 상세 페이지는 [OpenSheetMusicDisplay](https://opensheetmusicdisplay.org/)를
  CDN에서 불러와 악보를 화면에 바로 그려줍니다(선택 사항). CDN에 접근할 수 없는 환경이면
  자동으로 건너뛰고 다운로드 링크만 남으므로, 다른 기능에는 영향이 없습니다.

## 알려진 제한사항 / 다음 단계

- 검색은 게시글을 모두 불러와 제목/프롬프트/장르에 대해 부분일치로 필터링하는 단순한
  방식입니다 (규모가 커지면 Algolia 등 검색 서비스 연동을 고려).
- 생성된 오디오/악보는 Firebase Storage 대신 서버 로컬 디스크(`static/generated/`)에
  저장합니다. 배포 환경에 따라 Storage로 옮기는 것을 권장합니다.
- 좋아요/북마크, 댓글 삭제, 신고 기능은 아직 없습니다.
