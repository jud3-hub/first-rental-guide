"""홈런 최소 대시보드: Google Sheets 읽기 → 실험 비교 → Q01 답변 비교."""

import gspread
import pandas as pd
import streamlit as st

SHEET_ID = "1kvg4lgNtJ3nUugUMXFkYg0HxwuqgqrXR-Nw-KYrvN34"
EXPERIMENTS = ["EXP01", "EXP06"]
QUESTIONS = {"Q01", "Q04", "Q05"}
RUBRIC = "rubric-v2"
REQUIRED = [
    "실험", "실행 ID", "질문 ID", "유형", "모델", "프롬프트", "점수 /10",
    "치명 오류(AI)", "필수 동작", "실행 상태", "모델 답변", "루브릭 버전",
    "허위 절차(AI)", "근거 없는 수치(AI)", "사람 검토",
    "최종 치명 오류(사람)", "검토자", "사람 판단 근거",
]


def table_from_rows(rows, required):
    """제목과 빈 줄이 있어도 열 이름으로 실제 표 시작 위치 찾기."""
    for i, row in enumerate(rows):
        headers = [str(value).strip() for value in row]
        if set(required).issubset(headers):
            width = len(headers)
            body = [list(r[:width]) + [""] * max(0, width - len(r))
                    for r in rows[i + 1:] if any(str(v).strip() for v in r)]
            return pd.DataFrame(body, columns=headers)
    raise ValueError("필수 열을 찾지 못했습니다: " + " · ".join(required))


@st.cache_data(ttl=60, show_spinner=False)
def load_data():
    """서비스 계정으로 Sheets API 읽기만 수행. 결과는 60초 캐시."""
    account = dict(st.secrets["gcp_service_account"])
    client = gspread.service_account_from_dict(
        account,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    book = client.open_by_key(SHEET_ID)
    results = book.worksheet("결과 데이터").get(
        "A1:T200", value_render_option="UNFORMATTED_VALUE"
    )
    summary = book.worksheet("실험 비교").get(
        "A1:N65", value_render_option="UNFORMATTED_VALUE"
    )
    references = book.worksheet("평가 기준").get(
        "A1:E24", value_render_option="UNFORMATTED_VALUE"
    )
    return results, summary, references


def prepare_data(raw_results, raw_summary, raw_references):
    """화면에 쓸 데이터와 키 · 점수 · 실행 상태 확인."""
    results = table_from_rows(raw_results, REQUIRED)
    # 다른 평가 버전은 현재 3문항 비교와 섞지 않음.
    results = results[
        results["실험"].isin(EXPERIMENTS) & (results["루브릭 버전"] == RUBRIC)
    ].copy()
    for col in REQUIRED:
        if col != "점수 /10":
            results[col] = results[col].fillna("").astype(str).str.strip()
    raw_scores = results["점수 /10"].replace("", pd.NA)
    results["점수 /10"] = pd.to_numeric(raw_scores, errors="coerce")
    invalid_scores = (raw_scores.notna() & results["점수 /10"].isna()) | (
        results["점수 /10"].notna()
        & ~results["점수 /10"].between(0, 10)
    )
    if invalid_scores.any():
        raise ValueError("점수 열에 숫자가 아니거나 0~10 범위를 벗어난 값이 있습니다.")
    keys = ["실험", "실행 ID", "질문 ID", "루브릭 버전"]
    if results.duplicated(keys).any():
        raise ValueError("실행 · 질문 · 루브릭이 같은 중복 행이 있습니다.")
    for exp in EXPERIMENTS:
        part = results[results["실험"] == exp]
        if len(part) != 3 or set(part["질문 ID"]) != QUESTIONS:
            raise ValueError(f"{exp}: Q01 · Q04 · Q05 각 1행이 필요합니다. 반복 실행은 실행 ID별로 분리해 주세요.")
        if part["실행 ID"].nunique() != 1 or not part["실행 ID"].iloc[0]:
            raise ValueError(f"{exp}: 실행 ID가 없거나 서로 다른 실행의 답변이 섞였습니다.")
        if part["모델"].nunique() != 1 or not part["모델"].iloc[0]:
            raise ValueError(f"{exp}: 모델 정보를 확인해 주세요.")
    results["검토 완료"] = (
        (results["사람 검토"] == "완료")
        & results["최종 치명 오류(사람)"].isin(["있음", "없음"])
        & results["검토자"].ne("")
        & results["사람 판단 근거"].ne("")
    )
    summary = table_from_rows(raw_summary, ["실험", "프롬프트", "v2 AI 점수 /30", "확정 위험 문항"])
    summary["실험 ID"] = summary["실험"].astype(str).str.extract(r"^(EXP\d+)\s*·")
    summary = summary[summary["실험 ID"].isin(EXPERIMENTS)].copy()
    if set(summary["실험 ID"]) != set(EXPERIMENTS) or summary["실험 ID"].duplicated().any():
        raise ValueError("실험 비교 탭에서 EXP01 · EXP06 요약을 각 1행씩 확인해 주세요.")
    references = table_from_rows(raw_references, ["ID", "질문", "기준 답변", "근거 조문"])
    q01 = references[references["ID"] == "Q01"]
    if len(q01) != 1:
        raise ValueError("평가 기준 탭에서 Q01 기준 답변을 확인해 주세요.")
    return results, summary.set_index("실험 ID"), q01.iloc[0]


def main():
    st.set_page_config(page_title="홈런 · LLM 성능 비교", page_icon="🏠", layout="wide")
    st.title("홈런 · LLM 성능 비교")
    st.caption("EXP01 · EXP06 비교 / 기존 실험 결과 열람 / 모델 추론 없음")
    if st.button("최신 데이터 불러오기"):
        load_data.clear()
    try:
        with st.spinner("Google Sheets 결과를 읽는 중…"):
            results, summary, reference = prepare_data(*load_data())
    except (KeyError, FileNotFoundError):
        st.info("Google Sheets 연결 설정이 필요합니다. README의 서비스 계정 설정을 완료한 뒤 Secrets에 등록해 주세요.")
        st.stop()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    except Exception:
        st.error("Google Sheets를 읽지 못했습니다. Sheets API 활성화 · 서비스 계정의 뷰어 권한 · Secrets 형식을 확인해 주세요.")
        st.stop()

    left, right = st.columns(2)
    label = lambda exp: str(summary.loc[exp, "실험"])
    base = left.selectbox("기준 실험", EXPERIMENTS, index=0, format_func=label)
    target = right.selectbox("비교 실험", EXPERIMENTS, index=1, format_func=label)
    st.caption("평가 범위: 개발용 Q01 · Q04 · Q05 / rubric-v2 / 최대 60초 캐시")
    if base == target:
        st.info("같은 실험을 선택했습니다. 다른 실험을 선택하면 변경 전후를 비교할 수 있습니다.")

    st.subheader("1. 전체 결과 비교")
    totals, criticals, checked = {}, {}, {}
    for exp in dict.fromkeys([base, target]):
        part = results[results["실험"] == exp]
        totals[exp] = part["점수 /10"].sum(min_count=3)
        checked[exp] = int(part["검토 완료"].sum())
        criticals[exp] = int((part["검토 완료"] & (part["최종 치명 오류(사람)"] == "있음")).sum())
        if pd.notna(totals[exp]) and totals[exp] != pd.to_numeric(summary.loc[exp, "v2 AI 점수 /30"], errors="coerce"):
            st.warning(f"{exp}: 질문별 합계와 요약 탭 총점이 다릅니다. 아래에는 질문별 합계를 표시합니다.")
        if checked[exp] == 3 and criticals[exp] != pd.to_numeric(summary.loc[exp, "확정 위험 문항"], errors="coerce"):
            st.warning(f"{exp}: 사람 확정 오류 건수가 요약 탭과 다릅니다.")
        if not part["실행 상태"].eq("ok").all():
            st.warning(f"{exp}: 정상 완료가 아닌 실행이 있습니다. 답변의 실행 상태를 확인해 주세요.")
    a, b, c = st.columns(3)
    delta = None if any(pd.isna(totals[x]) for x in [base, target]) else f"{totals[target] - totals[base]:+.0f}점"
    a.metric("비교 실험 AI 총점", "미채점 포함" if pd.isna(totals[target]) else f"{totals[target]:.0f} / 30점", delta=delta)
    b.metric("기준 실험 AI 총점", "미채점 포함" if pd.isna(totals[base]) else f"{totals[base]:.0f} / 30점")
    c.metric("사람 확정 치명적 오류", f"{criticals[base]} → {criticals[target]}건", delta=None)
    st.caption(f"치명적 오류 검토 완료: {base} {checked[base]}/3건 · {target} {checked[target]}/3건. 미검토는 오류 없음이 아닙니다.")
    st.bar_chart(pd.DataFrame({"실험": list(totals), "AI 총점": list(totals.values())}).set_index("실험"), y_label="점수 / 최대 30점")
    st.caption("질문 3개 · 실험별 1회 실행의 개발용 결과. 전체 법률 상담 성능을 의미하지 않음.")

    st.subheader("2. 실험 설정 비교")
    settings = []
    for exp in [base, target]:
        row = results[results["실험"] == exp].iloc[0]
        settings.append({"실험": exp, "오픈소스 LLM · 모델": row["모델"],
                         "프롬프트 · 기록 버전": row["프롬프트"], "실행 ID": row["실행 ID"],
                         "루브릭": row["루브릭 버전"]})
    st.dataframe(pd.DataFrame(settings), hide_index=True, width="stretch")
    st.caption("위 설정은 시트에 기록된 값. RAG · 파인튜닝 등 상세 기술 설정은 이 최소 버전에서 표시하지 않음.")

    st.subheader("3. 질문별 상세 비교 · Q01")
    st.write(str(reference["질문"]))
    with st.expander("기준 답변 · 근거 조문"):
        st.write(str(reference["기준 답변"]))
        st.caption(str(reference["근거 조문"]))
    for exp, col in zip([base, target], st.columns(2)):
        row = results[(results["실험"] == exp) & (results["질문 ID"] == "Q01")].iloc[0]
        with col:
            st.markdown(f"**{label(exp)}**")
            score = "미채점" if pd.isna(row["점수 /10"]) else f"{row['점수 /10']:.0f} / 10점"
            st.metric("Q01 AI 점수", score)
            # 사용자/모델 텍스트를 HTML로 실행하지 않고 그대로 출력.
            st.text(str(row["모델 답변"]))
            st.caption(f"실행 상태: {row['실행 상태']}")
            with st.expander("오류 판정 · 사람 검토", expanded=True):
                st.write(f"AI 치명적 오류 후보: {row['치명 오류(AI)'] or '미판정'}")
                st.write(f"허위 절차(AI): {row['허위 절차(AI)'] or '미판정'}")
                st.write(f"근거 없는 수치(AI): {row['근거 없는 수치(AI)'] or '미판정'}")
                if row["검토 완료"]:
                    st.write(f"사람 확정 치명적 오류: {row['최종 치명 오류(사람)']}")
                    st.caption(f"검토자: {row['검토자']} / 치명적 오류 판정 검토")
                    st.text(str(row["사람 판단 근거"]))
                else:
                    st.info("사람 검토 미완료 · 최종 오류 판정 보류")
    st.caption("점수는 AI 채점 결과. 사람 검토 완료는 치명적 오류 판정에 대한 검토를 뜻함.")


if __name__ == "__main__":
    main()
