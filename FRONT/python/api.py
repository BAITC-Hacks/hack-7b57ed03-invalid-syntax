"""The desktop's only interface to the team's FastAPI backend."""
from pathlib import Path
from urllib.parse import urlparse

import httpx


class ApiError(RuntimeError):
    pass


class Api:
    def __init__(self, base_url: str):
        url = urlparse(base_url)
        if url.scheme != 'http' or url.hostname not in {'127.0.0.1', 'localhost', '::1'}:
            raise ValueError('Backend должен работать на этом компьютере (localhost).')
        self.base = base_url.rstrip('/')

    def request(self, method, path, **kwargs):
        try:
            with httpx.Client(base_url=self.base, timeout=180, trust_env=False) as client:
                response = client.request(method, path, **kwargs)
            if response.is_error:
                try:
                    detail = response.json().get('detail', response.text)
                except ValueError:
                    detail = response.text
                raise ApiError(f'Backend: {response.status_code}. {str(detail)[:600]}')
            return response
        except httpx.RequestError as exc:
            raise ApiError('Нет связи с локальным backend. Проверьте запуск приложения.') from exc

    def health(self):
        return self.request('GET', '/health').json()

    def meetings(self):
        return self.request('GET', '/api/v1/meetings').json()

    def meeting(self, meeting_id):
        return self.request('GET', f'/api/v1/meetings/{meeting_id}').json()

    def create(self, title, day):
        return self.request('POST', '/api/v1/meetings', json={
            'title': title.strip(), 'meeting_date': day,
        }).json()

    def upload(self, meeting_id, path):
        path = Path(path)
        if not path.is_file() or not 0 < path.stat().st_size <= 500 * 1024 * 1024:
            raise ApiError('Нужен непустой файл размером до 500 МБ.')
        with path.open('rb') as file:
            return self.request('POST', f'/api/v1/meetings/{meeting_id}/upload',
                                files={'file': (path.name, file)}).json()

    def process(self, meeting_id):
        return self.request('POST', f'/api/v1/meetings/{meeting_id}/process').json()

    def status(self, meeting_id):
        return self.request('GET', f'/api/v1/meetings/{meeting_id}/status').json()

    def task(self, meeting_id, task_id, values):
        return self.request('PATCH', f'/api/v1/meetings/{meeting_id}/tasks/{task_id}', json=values).json()

    def participant(self, meeting_id, participant_id, values):
        return self.request('PATCH', f'/api/v1/meetings/{meeting_id}/participants/{participant_id}',
                            json=values).json()

    def media_url(self, meeting_id):
        return f'{self.base}/api/v1/meetings/{meeting_id}/media'

    def export(self, meeting_id, kind, destination):
        if kind not in {'pdf', 'docx'}:
            raise ValueError('Unsupported export type')
        content = self.request('GET', f'/api/v1/meetings/{meeting_id}/export/{kind}').content
        destination = Path(destination)
        temporary = destination.with_suffix(destination.suffix + '.part')
        try:
            temporary.write_bytes(content)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination
