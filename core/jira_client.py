import requests

class JiraClient:
    def __init__(self, jira_url, username, api_token):
        self.jira_url = jira_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.session = requests.Session()
        self.session.auth = (username, api_token)
        self.session.headers.update({'Accept': 'application/json'})

    def test_connection(self):
        """
        Jira 연결 테스트 - 성공시 유저 정보 반환, 실패시 예외
        """
        url = f"{self.jira_url}/rest/api/3/myself"
        resp = self.session.get(url, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"JIRA 연결 실패: {resp.status_code} - {resp.text}")
        return resp.json()