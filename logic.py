import sqlite3
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any
import requests

skills = [ (_,) for _ in (['Python', 'SQL', 'API', 'Telegram'])]
statuses = [ (_,) for _ in (['На этапе проектирования', 'В процессе разработки', 'Разработан. Готов к использованию.', 'Обновлен', 'Завершен. Не поддерживается'])]

@dataclass
class Project:
    project_id: int = 0
    user_id: int = 0
    project_name: str = ""
    description: str = ""
    url: str = ""
    status_id: int = 0
    status_name: str = "" # временно, в идеале надо будет создавать отдельный объект, но это в значительной мере усложняет структуру
    @classmethod
    def factory(cls, cursor: sqlite3.Cursor, row: tuple[str | int, ...]) -> "Project":
        project = Project()
        for i, column in enumerate(cursor.description):
            if column[0] in cls.__dataclass_fields__:
                setattr(project, column, row[i])




class DBManager:
    def __init__(self, database: str):
        self.database = database # имя базы данных
        
    def create_tables(self):
        con = sqlite3.connect(self.database)
        cur = con.cursor()
        with con:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS status
                (
                    status_id INTEGER PRIMARY KEY,
                    status_name TEXT UNIQUE
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS skills
                (
                    skill_id INTEGER PRIMARY KEY,
                    skill_name TEXT UNIQUE
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS projects
                (
                    project_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    project_name TEXT UNIQUE,
                    description TEXT,
                    url TEXT,
                    status_id INTEGER REFERENCES status(status_id)
                    icon_content BLOB
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS projectskills
                (
                    skill_id INTEGER REFERENCES skills(skill_id),
                    project_id INTEGER REFERENCES projects(project_id)
                )
                """
            )
        con.close() 

    def __executemany(self, sql, data):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany(sql, data)
        conn.close()

    def __select_data(self, sql, data = tuple(), 
                      row_factory: None | Callable[[sqlite3.Cursor, tuple[Any, ...]], Any] = None):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            if row_factory is not None:
                cur.row_factory = row_factory
            cur.execute(sql, data)
        res = cur.fetchall()
        conn.close()
        return res

    def default_insert(self):
        sql = 'INSERT OR IGNORE INTO skills (skill_name) VALUES(?)'
        data = skills
        self.__executemany(sql, data)
        sql = 'INSERT OR IGNORE INTO status (status_name) VALUES(?)'
        data = statuses
        self.__executemany(sql, data)

    def set_screenshot(self, project_id: int, url: str, filesize: int | None = None):
        sql = 'UPDATE "projects" SET "screenshot" = zeroblob(?) WHERE "project_id" = ?'

        conn = sqlite3.connect(self.database)
        response = requests.get(url, stream=True)        
        if filesize is None:
            filesize = int(response.headers["content-length"])

        with conn:
            cursor = conn.cursor()
            cursor.execute(sql, (filesize, project_id))
            with conn.blobopen("projects", "screenshot", project_id) as blob:
                for data in response.iter_content(1024):
                    blob.write(data)

        conn.close()

    def insert_project(self, data):
        sql = "INSERT INTO projects (user_id, project_name, url, description, status_id) VALUES (?, ?, ?, ?, ?)"
        # здесь не было колонки description
        # надо было её добавить
        # да, тут было только user_id, project_name, url и status_id
        # да
        # это всё
        # сейчас поделюсь окном телеграма
        # возможно
        self.__executemany(sql, data)


    def insert_skill(self, user_id, project_name, skill):
        sql = 'SELECT project_id FROM projects WHERE project_name = ? AND user_id = ?'
        project_id = self.__select_data(sql, (project_name, user_id))[0][0]
        skill_id = self.__select_data('SELECT skill_id FROM skills WHERE skill_name = ?', (skill,))[0][0]
        data = [(project_id, skill_id)]
        sql = 'INSERT OR IGNORE INTO projectskills (project_id, skill_id) VALUES(?, ?)'
        self.__executemany(sql, data)

    def set_desc_by_name(self, project_name: str, user_id: int, desc: str) -> None:
        project_id_query = "SELECT project_id FROM projects WHERE project_name = ? AND user_id = ?"
        
        project_id = self.__select_data(project_id_query, (project_name, user_id))[0][0]
        
        update_query = "UPDATE projects SET description = ? WHERE project_id = ?"
        
        self.__executemany(update_query, [(desc, project_id)])

    def get_statuses(self):
        sql = "SELECT status_name FROM status"
        return self.__select_data(sql)
        

    def get_status_id(self, status_name):
        sql = 'SELECT status_id FROM status WHERE status_name = ?'
        res = self.__select_data(sql, (status_name,))
        if res: return res[0][0]
        else: return None

    def get_projects(self, user_id) -> list[Project]:
        sql = "SELECT * FROM projects WHERE user_id = ?"
        return self.__select_data(sql, data = (user_id,), row_factory=Project.factory)
        
    def get_project_id(self, project_name, user_id) -> int:
        return self.__select_data(sql='SELECT project_id FROM projects WHERE project_name = ? AND user_id = ?  ', data = (project_name, user_id,))[0][0]
        
    def get_skills(self) -> list[tuple]:
        return self.__select_data(sql='SELECT * FROM skills')
    
    def get_project_skills(self, project_name: str) -> str:
        res = self.__select_data(sql='''SELECT skill_name FROM projects 
JOIN projectskills ON projects.project_id = projectskills.project_id 
JOIN skills ON skills.skill_id = projectskills.skill_id 
WHERE project_name = ?''', data = (project_name,) )
        return ', '.join([x[0] for x in res])
    
    def get_project_info(self, user_id: int, project_name: str) -> list[Project]:
        sql = """
SELECT project_name, description, url, status_name FROM projects 
JOIN status ON
status.status_id = projects.status_id
WHERE project_name=? AND user_id=?
"""
        return self.__select_data(sql=sql, data = (project_name, user_id), row_factory=Project.factory)


    def update_projects(self, param, data):
        sql = "UPDATE projects SET {param} = ? WHERE project_name = ? AND user_id = ?"
        self.__executemany(sql, [data]) 


    def delete_project(self, user_id, project_id):
        sql = "DELETE FROM projects WHERE project_id = ? AND user_id = ?"
        self.__executemany(sql, [(project_id, user_id)])
    
    def delete_skill(self, project_id, skill_id):
        sql = "DELETE FROM skills WHERE skill_id = ? AND project_id = ?"
        self.__executemany(sql, [(skill_id, project_id)])

    def set_icon(self, project_id: int, icon_content: bytes) -> None:
        sql = "UPDATE projects SET icon = ? WHERE project_id = ?"
        self.__executemany(sql, [(project_id, icon_content)])