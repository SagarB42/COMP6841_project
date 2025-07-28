DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS posts;

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  first_name TEXT,
  last_name TEXT,
  profile_pic_url TEXT
);

CREATE TABLE posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  author_id INTEGER NOT NULL,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  visibility TEXT NOT NULL DEFAULT 'public',
  FOREIGN KEY (author_id) REFERENCES users (id)
);

INSERT INTO users (username, password, role) VALUES ('admin', 'password', 'admin');
INSERT INTO users (username, password, role) VALUES ('supreme_user', 'iHeaRtcoMP6841', 'admin');
INSERT INTO users (username, password, role) VALUES ('user', 'password', 'user');
INSERT INTO users (username, password, role) VALUES ('sagar', 'sagar', 'user');

INSERT INTO posts (author_id, title, content, visibility) VALUES (1, 'Admin Public Post', 'This is a public post by the admin.', 'public');
INSERT INTO posts (author_id, title, content, visibility) VALUES (1, 'Admin Private Post', 'This is a SECRET private post by the admin.', 'private');
INSERT INTO posts (author_id, title, content, visibility) VALUES (2, 'User Public Post', 'Hello world, from a regular user.', 'public');
INSERT INTO posts (author_id, title, content, visibility) VALUES (4, 'First Post', 'THIS IS MY FIRST POST!', 'public');
INSERT INTO posts (author_id, title, content, visibility) VALUES (4, 'EXCITED!!!', 'Excited to be in COMP6841', 'private');

