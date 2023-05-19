import psycopg2 as pg

class Database():
    def __init__(self, parameters) -> None:
        self.connection = pg.connect(
            host=parameters['host'],
            user=parameters['user'],
            password=parameters['password'],
            database=parameters['db_name'],
            port=5432
        )

        self.cursor = self.connection.cursor()

    def add_user(self, user):
        with self.connection:
            try:
                return self.cursor.execute('INSERT INTO users (id, sex, age, city, offset_list) VALUES (%s, %s, %s, %s, 0)', (user.id, user.sex, user.age, user.city))

            except pg.IntegrityError:
                return False
            
    def add_found(self, user_id, search_id, description):
        with self.connection:
            self.cursor.execute('INSERT INTO found_users (id, id_user, description) VALUES (%s, %s, %s)', (search_id, user_id, description))
            
    def add_seen(self, user_id, seen_id, description):
        with self.connection:
            # descr_for_db = description.replace('\n', ':')
            descr_for_db = description
            self.cursor.execute('SELECT * FROM seen_users WHERE id_seen = %s AND id_user = %s', (seen_id, user_id))
            if not self.cursor.fetchone():
                self.cursor.execute('INSERT INTO seen_users (id_user, id_seen, description) VALUES (%s, %s, %s)', (user_id, seen_id, descr_for_db))

    def add_fav(self, user_id, fav_id, description):
        with self.connection:
            # descr_for_db = description.replace('\n', ':')
            descr_for_db = description
            self.cursor.execute('SELECT * FROM fav_users WHERE id_fav = %s AND id_user = %s', (fav_id, user_id))
            if not self.cursor.fetchone():
                self.cursor.execute('INSERT INTO fav_users (id_user, id_fav, description) VALUES (%s, %s, %s)', (user_id, fav_id, descr_for_db))

    def get_ids_user(self) -> list:
        with self.connection:
            self.cursor.execute('SELECT id FROM users')
            return self.cursor.fetchall()        

    def get_user(self, user_id) -> dict:
        with self.connection:
            result = {}

            data = self.cursor.execute('SELECT * FROM users WHERE id=%s', (user_id, ))
            data = self.cursor.fetchone()
            result['id'] = data[0]
            result['age'] = data[1]
            result['city'] = data[2]
            result['sex'] = data[3]
            result['offset'] = data[4]
            return result
        
    def get_found_user(self, number, search_id):
        with self.connection:
            self.cursor.execute('SELECT * FROM found_users WHERE id = %s', (search_id, ))
            return self.cursor.fetchall()[number]
        
    def get_seen_list(self, user_id) -> dict:
        with self.connection:
            self.cursor.execute('SELECT id_seen, description FROM seen_users WHERE id_user = %s', (user_id,))
            return self.cursor.fetchall()
        
    def get_fav_list(self, user_id) -> dict:
        with self.connection:
            self.cursor.execute('SELECT id_fav, description FROM fav_users WHERE id_user = %s', (user_id,))
            return self.cursor.fetchall()
        
    def users_for_check(self) -> list:
        with self.connection:
            self.cursor.execute('SELECT id, last_date, status FROM users WHERE status=1;')
            return self.cursor.fetchall()
        
    def get_description(self, seen_id) -> str:
        with self.connection:
            self.cursor.execute('SELECT description FROM seen_users WHERE id_seen = %s', (seen_id,))
            return self.cursor.fetchone()[0]

    def update_offset(self, user):
        with self.connection:
            print(user.offset, user.id)
            self.cursor.execute('UPDATE users SET offset_list=%s WHERE id=%s', (user.offset, user.id))

    def update_status_and_date(self, user, date):
        with self.connection:
            self.cursor.execute('UPDATE users SET status=1 WHERE id=%s', (user.id, ))
            self.cursor.execute('UPDATE users SET last_date=%s WHERE id=%s', (date, user.id))

    def reset_status(self, user_id):
        with self.connection:
            self.cursor.execute('UPDATE users SET status=0;', (user_id, ))

    def create_table_users(self):
        with self.connection:
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS public.users
                (
                    id integer NOT NULL,
                    age integer,
                    city integer,
                    sex integer,
                    offset_list integer,
                    last_date integer,
                    status integer,
                    CONSTRAINT users_pkey PRIMARY KEY (id)
                );"""
            )

    def create_table_found_users(self):
        with self.connection:
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS public.found_users
                (
                    id bigint NOT NULL,
                    id_user bigint NOT NULL,
                    description text,
                    CONSTRAINT found_person_pkey PRIMARY KEY (id, id_user)
                )"""
            )
        
    def create_table_seen_users(self):
        with self.connection:
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS public.seen_users
                (
                    id serial NOT NULL,
                    id_user integer,
                    id_seen integer,
                    description text,
                    CONSTRAINT seen_users_pkey PRIMARY KEY (id)
                )"""
            )

    def create_table_fav_users(self):
        with self.connection:
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS public.fav_users
                (
                    id serial NOT NULL,
                    id_user integer,
                    id_fav integer,
                    description text,
                    CONSTRAINT fav_users_pkey PRIMARY KEY (id)
                )"""
            )

    def delete_table_seen_person(self):
        with self.connection:
            self.cursor.execute(
                """DROP TABLE  IF EXISTS seen_person CASCADE;"""
            )

if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8-sig')

    parameters_sql = config['POSTGRESQL']
    db = Database(parameters_sql)
    db.create_table_users()
    db.create_table_fav_users()
    db.create_table_found_users()
    db.create_table_seen_users()
    print("Database was created!")
