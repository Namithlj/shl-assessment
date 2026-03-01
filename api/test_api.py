import json
from api import server


def run_test():
    client = server.app.test_client()
    r = client.get('/health')
    print('Health:', r.status_code, r.get_json())

    payload = {"query": "Java developer with teamwork skills", "k": 5}
    r2 = client.post('/recommend', json=payload)
    print('Recommend status:', r2.status_code)
    print(json.dumps(r2.get_json(), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    run_test()
