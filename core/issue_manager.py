    @staticmethod
    def count_by_status(issues):
        """상태별 이슈 수 dict 반환"""
        from collections import Counter
        counts = Counter()
        for i in issues:
            name = (i['fields'].get('status') or {}).get('name', '알수없음')
            counts[name] += 1
        return dict(counts)

    @staticmethod
    def count_by_priority(issues):
        """우선순위별 이슈 수 dict 반환"""
        from collections import Counter
        counts = Counter()
        for i in issues:
            name = (i['fields'].get('priority') or {}).get('name', '알수없음')
            counts[name] += 1
        return dict(counts)

    @staticmethod
    def sort_issues_by_updated(issues, reverse=True):
        import dateutil.parser
        return sorted(issues, key=lambda i: dateutil.parser.parse(i['fields'].get('updated','')), reverse=reverse)
    def get_issue(self, issue_key):
        """특정 이슈 상세 조회"""
        url = f"{self.jira_client.jira_url}/rest/api/3/issue/{issue_key}"
        params = {"fields": "key,summary,description,status,assignee,priority,created,updated,comment"}
        resp = self.jira_client.session.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"이슈 상세 조회 실패: {resp.status_code} - {resp.text}")
        return resp.json()

    def get_available_statuses(self, issue_key):
        """이슈의 현재 워크플로우에서 이동 가능한 상태목록 반환"""
        url = f"{self.jira_client.jira_url}/rest/api/3/issue/{issue_key}/transitions"
        resp = self.jira_client.session.get(url, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"상태 조회 실패: {resp.status_code} - {resp.text}")
        transitions = resp.json().get("transitions", [])
        # 상태이름/ID 반환
        return [(t["name"], t["id"]) for t in transitions]

    def change_status(self, issue_key, transition_id):
        """이슈 상태 변경 (transition_id로)"""
        url = f"{self.jira_client.jira_url}/rest/api/3/issue/{issue_key}/transitions"
        data = {"transition": {"id": transition_id}}
        resp = self.jira_client.session.post(url, json=data, timeout=10)
        if resp.status_code not in (204, 200):
            raise Exception(f"상태 변경 실패: {resp.status_code} - {resp.text}")
        return True

    def add_comment(self, issue_key, comment):
        url = f"{self.jira_client.jira_url}/rest/api/3/issue/{issue_key}/comment"
        data = {"body": comment}
        resp = self.jira_client.session.post(url, json=data, timeout=10)
        if resp.status_code not in (201, 200):
            raise Exception(f"코멘트 추가 실패: {resp.status_code} - {resp.text}")
        return True

    def change_assignee(self, issue_key, username):
        url = f"{self.jira_client.jira_url}/rest/api/3/issue/{issue_key}/assignee"
        data = {"name": username}  # 일부 JIRA는 accountId도 가능, cloud환경에서는 accountId를 써야함
        resp = self.jira_client.session.put(url, json=data, timeout=10)
        if resp.status_code != 204:
            raise Exception(f"담당자 변경 실패: {resp.status_code} - {resp.text}")
        return True
class IssueManager:
    def __init__(self, jira_client):
        self.jira_client = jira_client

    def get_my_issues(self, statuses=None, max_results=50):
        """
        현재 로그인 계정에 할당된 이슈를 JIRA에서 조회
        :param statuses: 상태 목록 (예: ["To Do", "In Progress", "Done"])
        :param max_results: 최대 반환 개수
        :return: 이슈 리스트 (dict)
        """
        jql = "assignee=currentUser()"
        if statuses:
            status_str = ','.join([f'"{s}"' for s in statuses])
            jql += f" AND status in ({status_str})"
        url = f"{self.jira_client.jira_url}/rest/api/3/search"
        params = {
            "jql": jql,
            "fields": "key,summary,status,assignee,priority,created,updated",
            "maxResults": max_results
        }
        resp = self.jira_client.session.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            raise Exception(f"이슈 조회 실패: {resp.status_code} - {resp.text}")
        data = resp.json()
        return data.get('issues', [])