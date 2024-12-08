import sqlite3
from config import DATABASE

skills = [ (_,) for _ in (['Python', 'SQL', 'API', 'Telegram'])]
statuses = [ (_,) for _ in (['На этапе проектирования', 'В процессе разработки', 'Разработан. Готов к использованию.', 'Обновлен', 'Завершен. Не поддерживается'])]
DEFAULT_ICON = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512"><!--!Font Awesome Free 6.7.1 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.--><path d="M80 160c0-35.3 28.7-64 64-64l32 0c35.3 0 64 28.7 64 64l0 3.6c0 21.8-11.1 42.1-29.4 53.8l-42.2 27.1c-25.2 16.2-40.4 44.1-40.4 74l0 1.4c0 17.7 14.3 32 32 32s32-14.3 32-32l0-1.4c0-8.2 4.2-15.8 11-20.2l42.2-27.1c36.6-23.6 58.8-64.1 58.8-107.7l0-3.6c0-70.7-57.3-128-128-128l-32 0C73.3 32 16 89.3 16 160c0 17.7 14.3 32 32 32s32-14.3 32-32zm80 320a40 40 0 1 0 0-80 40 40 0 1 0 0 80z"/></svg>'

class DB_Manager:
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
                    status_name TEXT
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

    def __select_data(self, sql, data = tuple()):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
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


    def insert_project(self, data):
        sql = "INSERT INTO projects (user_id, project_name, url, status_id) VALUES (?, ?, ?, ?)"
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

    def get_projects(self, user_id):
        sql = "SELECT * FROM projects WHERE user_id = ?"
        return self.__select_data(sql, data = (user_id,))
        
    def get_project_id(self, project_name, user_id):
        return self.__select_data(sql='SELECT project_id FROM projects WHERE project_name = ? AND user_id = ?  ', data = (project_name, user_id,))[0][0]
        
    def get_skills(self):
        return self.__select_data(sql='SELECT * FROM skills')
    
    def get_project_skills(self, project_name) -> str:
        res = self.__select_data(sql='''SELECT skill_name FROM projects 
JOIN projectskills ON projects.project_id = projectskills.project_id 
JOIN skills ON skills.skill_id = projectskills.skill_id 
WHERE project_name = ?''', data = (project_name,) )
        return ', '.join([x[0] for x in res])
    
    def get_project_info(self, user_id, project_name):
        sql = """
SELECT project_name, description, url, status_name FROM projects 
JOIN status ON
status.status_id = projects.status_id
WHERE project_name=? AND user_id=?
"""
        return self.__select_data(sql=sql, data = (project_name, user_id))


    def update_projects(self, param, data):
        sql = "UPDATE projects SET {param} = ? WHERE project_name = ? AND user_id = ?"
        self.__executemany(sql, [data]) 


    def delete_project(self, user_id, project_id):
        sql = "DELETE FROM projects WHERE project_name = ? AND user_id = ?"
        self.__executemany(sql, [(user_id, project_id)])
    
    def delete_skill(self, project_id, skill_id):
        sql = "DELETE FROM skills WHERE skill_id = ? AND project_id = ?"
        self.__executemany(sql, [(skill_id, project_id)])

    def set_icon(self, project_id: int, icon_content: bytes) -> None:
        sql = "UPDATE projects SET icon = ? WHERE project_id = ?"
        self.__executemany(sql, [(project_id, icon_content)])