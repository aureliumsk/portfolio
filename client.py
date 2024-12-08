from argparse import ArgumentParser
from config import DATABASE
from logic import DB_Manager

def main():
    parser = ArgumentParser("portfolio")
    parser.add_argument("--type", "-t", choices=["project", "status"], dest="type", default="project")
    parser.add_argument("data", nargs="+")
    args = parser.parse_args()
    db = DB_Manager(DATABASE)
    db.default_insert()
    name, url, status_id = args.data[:3]
    status_id = int(status_id)
    if args.type == "project":
        # user_id, project_name, url, status_id
        db.insert_project(
            [(0, name, url, status_id)]
        )
        for skill in args.data[3:]:
            db.insert_skill(0, name, skill)
        print("Done!")
    else:
        raise NotImplementedError()

if __name__ == "__main__":
    main()
