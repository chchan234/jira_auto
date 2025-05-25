

from core.issue_manager import IssueManager
import streamlit as st

st.set_page_config(page_title="JIRA Manager", layout="centered")

# 1. 사이드바에 로그인/설정 입력

st.sidebar.title("🔐 JIRA 로그인/설정")
jira_url = st.sidebar.text_input("JIRA URL", "https://your-domain.atlassian.net")
username = st.sidebar.text_input("이메일 (User)")
api_token = st.sidebar.text_input("API Token", type="password")

# 연결 상태(세션) 저장을 위한 key 사용
if 'jira_authenticated' not in st.session_state:
    st.session_state.jira_authenticated = False
if 'jira_client' not in st.session_state:
    st.session_state.jira_client = None
if 'jira_user' not in st.session_state:
    st.session_state.jira_user = None

connect_btn = st.sidebar.button("연결 테스트")

if connect_btn:
    if not (jira_url and username and api_token):
        st.sidebar.error("모든 정보를 입력하세요.")
        st.session_state.jira_authenticated = False
    else:
        jclient = JiraClient(jira_url, username, api_token)
        try:
            user = jclient.test_connection()
            st.sidebar.success(f"연결 성공! ({user.get('displayName')})")
            st.session_state.jira_authenticated = True
            st.session_state.jira_client = jclient
            st.session_state.jira_user = user
        except Exception as e:
            st.sidebar.error(f"연결 실패: {e}")
            st.session_state.jira_authenticated = False

st.title("JIRA 관리 프로그램 (MVP)")
if not st.session_state.jira_authenticated:
    st.markdown("- 왼쪽에서 인증정보를 입력하고 연결을 테스트하세요.")
else:
    st.success(f"{st.session_state.jira_user.get('displayName')}님 환영합니다!")

    st.header("내 할당 이슈 목록")
    # 상태별 필터
    status_options = ["To Do", "In Progress", "Done"]
    status_selected = st.multiselect("상태별 필터", status_options, default=status_options)

    imgr = IssueManager(st.session_state.jira_client)
    try:
        issues = imgr.get_my_issues(statuses=status_selected)
        # 대시보드 표시
        st.markdown("## 📊 대시보드")
        total_cnt = len(issues)
        st.write(f"내 전체 이슈: **{total_cnt}건**")

        # 상태별 분포
        status_count = imgr.count_by_status(issues)
        st.write("상태별 이슈 수:")
        st.bar_chart(status_count)

        # 우선순위별 분포
        prio_count = imgr.count_by_priority(issues)
        st.write("우선순위별 이슈 수:")
        st.bar_chart(prio_count)

        # 최근 업데이트순 이슈(상위 5개)
        st.markdown("#### ⏰ 최근 업데이트된 이슈 5건")
        recent5 = imgr.sort_issues_by_updated(issues)[:5]
        if recent5:
            st.table([{
                '이슈키': i['key'],
                '제목': i['fields'].get('summary',''),
                '상태': (i['fields'].get('status') or {}).get('name',''),
                '담당자': (i['fields'].get('assignee') or {}).get('displayName',''),
                '수정': i['fields'].get('updated','')
            } for i in recent5])
        else:
            st.info("이슈 없음")

        # 테이블/선택용 데이터 가공
        table = []
        key_to_i = {}
        for i in issues:
            f = i['fields']
            key = i['key']
            key_to_i[key] = i
            table.append({
                '이슈키': key,
                '제목': f.get('summary',''),
                '상태': f.get('status',{}).get('name',''),
                '담당자': (f.get('assignee') or {}).get('displayName',''),
                '우선순위': (f.get('priority') or {}).get('name',''),
                '생성': f.get('created',''),
                '수정': f.get('updated','')
            })

        # 이슈 선택 UI 추가 (아래 동일)
        st.markdown("---")
        st.header("내 이슈 목록 및 편집")
        if table:
            st.dataframe(table, hide_index=True)
            issue_keys = [r['이슈키'] for r in table]
            sel_key = st.selectbox("상세/편집할 이슈 선택", options=[''] + issue_keys, format_func=lambda x: x or "---선택---")
            if sel_key:
                # 상세+액션 UI
                issue = imgr.get_issue(sel_key)
                f = issue['fields']
                st.subheader(f"{sel_key} - {f.get('summary','')}")
                st.markdown(f"**상태**: {f.get('status',{}).get('name','')}")
                st.markdown(f"**담당자**: {(f.get('assignee') or {}).get('displayName','-')}")
                st.markdown(f"**우선순위**: {(f.get('priority') or {}).get('name','-')}")
                st.markdown(f"**설명**: {f.get('description','없음')}")
                # 최근 코멘트 보여주기
                comments = (f.get('comment', {}) or {}).get('comments', [])
                st.markdown("**최근 코멘트**:")
                if comments:
                    for c in comments[-3:]:
                        st.info(f"{c.get('author',{}).get('displayName','')}: {c.get('body','')}")
                else:
                    st.code("코멘트 없음")

                # 상태 변경
                st.markdown("---")
                st.markdown("### 상태 변경")
                statuses = imgr.get_available_statuses(sel_key)
                if statuses:
                    stt_map = {name: tid for name, tid in statuses}
                    stt_choice = st.selectbox("상태 이동", options=[s[0] for s in statuses])
                    if st.button("상태 변경 실행"):
                        try:
                            imgr.change_status(sel_key, stt_map[stt_choice])
                            st.success("상태 변경 완료! 새로고침해주세요.")
                        except Exception as e:
                            st.error(str(e))
                else:
                    st.warning("가능한 상태 없음 (워크플로우 제한)")

                # 코멘트 추가
                st.markdown("### 코멘트 추가")
                new_comment = st.text_area("코멘트 입력")
                if st.button("코멘트 등록"):
                    if not new_comment.strip():
                        st.warning("코멘트를 입력하세요.")
                    else:
                        try:
                            imgr.add_comment(sel_key, new_comment)
                            st.success("코멘트 등록 완료! 새로고침해주세요.")
                        except Exception as e:
                            st.error(str(e))

                # 담당자 변경 — 심플(현재 담당자만 텍스트 수정, 추후 계정목록연동 권장)
                st.markdown("### 담당자 변경")
                new_assignee = st.text_input("신규 담당자 이름(Jira username, Cloud는 accountId 필요)")
                if st.button("담당자 변경"):
                    if not new_assignee:
                        st.warning("담당자를 입력하세요.")
                    else:
                        try:
                            imgr.change_assignee(sel_key, new_assignee)
                            st.success("담당자 변경 완료! 새로고침해주세요.")
                        except Exception as e:
                            st.error(str(e))
        else:
            st.info("해당 조건의 이슈가 없습니다.")
    except Exception as e:
        st.error(f"이슈 목록 불러오기 오류: {e}")